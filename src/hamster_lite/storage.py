# - coding: utf-8 -

# Copyright (C) 2007-2009, 2012, 2014 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (C) 2007 Patryk Zawadzki <patrys at pld-linux.org>

# This file is part of Project Hamster.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Project Hamster.  If not, see <http://www.gnu.org/licenses/>.


"""Storage / database operations"""

import logging
logger = logging.getLogger(__name__)   # noqa: E402

import os, time
import datetime
import itertools
import sqlite3
from shutil import copy as copyfile
import datetime as dt
from hamster_lite.lib import Fact
from hamster_lite.lib.configuration import conf
from hamster_lite.lib.stuff import hamster_today, hamster_now

UNSORTED_ID = -1

class Storage():
    con = None # Connection will be created on demand
    def __init__(self, unsorted="Unsorted", database_dir=None):
        """
        Delayed setup so we don't do everything at the same time (?)
        """
        self._unsorted = unsorted # NB. pass in localized name

        self.__con = None
        self.__cur = None

        self.db_path = self.__init_db_file(database_dir)
        logger.info("database: '{}'".format(self.db_path))

        self.run_fixtures()

    def __init_db_file(self, database_dir):
        if not database_dir:
            try:
                from xdg.BaseDirectory import xdg_data_home
            except ImportError:
                logger.warning("Could not import xdg - assuming ~/.local/share")
                xdg_data_home = os.path.join(os.path.expanduser('~'), '.local', 'share')
            database_dir = os.path.join(xdg_data_home, 'hamster-lite')

        if not os.path.exists(database_dir):
            os.makedirs(database_dir, 0o744)

        db_path = os.path.join(database_dir, "hamster.db")

        # check if we have a database at all
        if not os.path.exists(db_path):
            # handle pre-existing hamster-applet database
            old_db_path = os.path.join(xdg_data_home, 'hamster-applet', 'hamster.db')
            if os.path.exists(old_db_path):
                logger.warning("Linking %s to %s" % (old_db_path, db_path))
                os.link(old_db_path, db_path)
            else:
                # make a copy of the empty template hamster.db
                try:
                    from hamster import defs
                    data_dir = os.path.join(defs.DATA_DIR, "hamster-lite")
                except:
                    # if defs is not there, we are running from sources
                    module_dir = os.path.dirname(os.path.realpath(__file__))
                    if os.path.exists(os.path.join(module_dir, "data")):
                        # running as flask app. XXX - detangle
                        data_dir = os.path.join(module_dir, "data")
                    else:
                        # get ./data from ./src/hamster_lite/storage/db.py (3 levels up)
                        data_dir = os.path.join(module_dir, '..', '..', '..', 'data')
                logger.warning("Database not found in %s - installing default from %s!"
                               % (db_path, data_dir))
                copyfile(os.path.join(data_dir, 'hamster.db'), db_path)

            #change also permissions - sometimes they are 444
            os.chmod(db_path, 0o664)

        db_path = os.path.realpath(db_path) # needed for file monitoring?

        return db_path


    # facts
    def update_fact(self, fact_id, fact, temporary = False):
        self.start_transaction()
        self._remove_fact(fact_id)
        result = self.add_fact(fact, temporary)
        self.end_transaction()
        return result

    def remove_fact(self, fact_id):
        """Remove fact from storage by it's ID"""
        self.start_transaction()
        fact = self.get_fact(fact_id)
        if fact:
            self._remove_fact(fact_id)
        self.end_transaction()

    def stop_tracking(self, end_time=None):
        """Stops tracking the current activity"""
        facts = self.get_todays_facts()
        if facts and not facts[-1].end_time:
            self._touch_fact(facts[-1], end_time or hamster_now())


    #tags, here we come!
    def get_tags(self, only_autocomplete = False):
        if only_autocomplete:
            return self.fetchall("select * from tags where autocomplete != 'false' order by name")
        else:
            return self.fetchall("select * from tags order by name")

    def _get_tag_ids(self, tags):
        """look up tags by their name. create if not found"""

        # bit of magic here - using sqlites bind variables
        db_tags = self.fetchall("select * from tags where name in (%s)"
                                % ",".join(["?"] * len(tags)), tags)

        changes = False

        # check if any of tags needs resurrection
        set_complete = [str(tag["id"]) for tag in db_tags if tag["autocomplete"] == "false"]
        if set_complete:
            changes = True
            self.execute("update tags set autocomplete='true' where id in (%s)" % ", ".join(set_complete))


        found_tags = [tag["name"] for tag in db_tags]

        add = set(tags) - set(found_tags)
        if add:
            statement = "insert into tags(name) values(?)"

            self.execute([statement] * len(add), [(tag,) for tag in add])

            return self._get_tag_ids(tags)[0], True # all done, recurse
        else:
            return db_tags, changes

    def __update_autocomplete_tags(self, tags):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]  # split by comma

        #first we will create new ones
        tags, changes = self._get_tag_ids(tags)
        tags = [tag["id"] for tag in tags]

        #now we will find which ones are gone from the list
        query = """
                    SELECT b.id as id, b.autocomplete, count(a.fact_id) as occurences
                      FROM tags b
                 LEFT JOIN fact_tags a on a.tag_id = b.id
                     WHERE b.id not in (%s)
                  GROUP BY b.id
                """ % ",".join(["?"] * len(tags)) # bit of magic here - using sqlites bind variables

        gone = self.fetchall(query, tags)

        to_delete = [str(tag["id"]) for tag in gone if tag["occurences"] == 0]
        to_uncomplete = [str(tag["id"]) for tag in gone if tag["occurences"] > 0 and tag["autocomplete"] == "true"]

        if to_delete:
            self.execute("delete from tags where id in (%s)" % ", ".join(to_delete))

        if to_uncomplete:
            self.execute("update tags set autocomplete='false' where id in (%s)" % ", ".join(to_uncomplete))

        return changes or len(to_delete + to_uncomplete) > 0

    def get_categories(self):
        return self.fetchall("SELECT id, name FROM categories ORDER BY lower(name)")

    def update_activity(self, id, name, category_id):
        query = """
                   UPDATE activities
                       SET name = ?,
                           search_name = ?,
                           category_id = ?
                     WHERE id = ?
        """
        self.execute(query, (name, name.lower(), category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        self._remove_index(affected_ids)


    def change_category(self, id, category_id):
        # first check if we don't have an activity with same name before us
        activity = self.fetchone("select name from activities where id = ?", (id, ))
        existing_activity = self.get_activity_by_name(activity['name'], category_id)

        if existing_activity and id == existing_activity['id']: # we are already there, go home
            return False

        if existing_activity: #ooh, we have something here!
            # first move all facts that belong to movable activity to the new one
            update = """
                       UPDATE facts
                          SET activity_id = ?
                        WHERE activity_id = ?
            """

            self.execute(update, (existing_activity['id'], id))

            # and now get rid of our friend
            self.remove_activity(id)

        else: #just moving
            statement = """
                       UPDATE activities
                          SET category_id = ?
                        WHERE id = ?
            """

            self.execute(statement, (category_id, id))

        affected_ids = [res[0] for res in self.fetchall("select id from facts where activity_id = ?", (id,))]
        if existing_activity:
            affected_ids.extend([res[0] for res in self.fetchall("select id from facts where activity_id = ?", (existing_activity['id'],))])
        self._remove_index(affected_ids)

        return True

    def add_category(self, name):
        query = """
                   INSERT INTO categories (name, search_name)
                        VALUES (?, ?)
        """
        self.execute(query, (name, name.lower()))
        return self._last_insert_rowid()

    def update_category(self, id,  name):
        if id > -1: # Update, and ignore unsorted, if that was somehow triggered
            update = """
                       UPDATE categories
                           SET name = ?, search_name = ?
                         WHERE id = ?
            """
            self.execute(update, (name, name.lower(), id))

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]
        self._remove_index(affected_ids)


    def get_activity_by_name(self, activity, category_id = None, resurrect = True):
        """get most recent, preferably not deleted activity by it's name"""

        if category_id:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                          AND category_id = ?
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """

            res = self.fetchone(query, (self._unsorted, activity, category_id))
        elif activity:
            query = """
                       SELECT a.id, a.name, a.deleted, coalesce(b.name, ?) as category
                         FROM activities a
                    LEFT JOIN categories b ON category_id = b.id
                        WHERE lower(a.name) = lower(?)
                     ORDER BY a.deleted, a.id desc
                        LIMIT 1
            """
            res = self.fetchone(query, (self._unsorted, activity, ))
        else:
            res = None

        if res:
            keys = ('id', 'name', 'deleted', 'category')
            res = dict([(key, res[key]) for key in keys])
            res['deleted'] = res['deleted'] or False

            # if the activity was marked as deleted, resurrect on first call
            # and put in the unsorted category
            if res['deleted'] and resurrect:
                update = """
                            UPDATE activities
                               SET deleted = null, category_id = -1
                             WHERE id = ?
                        """
                self.execute(update, (res['id'], ))

            return res

        return {}

    def get_category_id(self, name):
        """returns category by it's name"""
        if not name:
            return UNSORTED_ID

        query = """
                   SELECT id from categories
                    WHERE lower(name) = lower(?)
                 ORDER BY id desc
                    LIMIT 1
        """

        res = self.fetchone(query, (name, ))

        if res:
            return res['id']

        return None


    def get_fact(self, id):
        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS activity, b.id as activity_id,
                          coalesce(c.name, ?) as category, coalesce(c.id, -1) as category_id,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE a.id = ?
                 ORDER BY e.name
        """

        rows = self.fetchall(query, (self._unsorted, id))
        assert len(rows) > 0, "No fact with id {}".format(id)
        fact = self._create_facts(rows)[0]
        logger.info("got fact {}".format(fact))
        return fact

    def _create_facts(self, fact_dicts):
        """Create Fact instances, moving all tags to an array"""
        if not fact_dicts: return fact_dicts  #be it None or whatever

        facts = []
        for fact_id, fact_tags in itertools.groupby(fact_dicts, lambda f: f["id"]):
            fact_tags = list(fact_tags)

            # first one is as good as the last one: convert to Fact
            grouped_fact = Fact(**fact_tags[0])
            grouped_fact.tags = [ft["tag"] for ft in fact_tags if ft["tag"]]

            facts.append(grouped_fact)
        return facts


    def _touch_fact(self, fact, end_time = None):
        end_time = end_time or hamster_now()
        # tasks under one minute do not count
        if end_time - fact.start_time < datetime.timedelta(minutes = 1):
            self._remove_fact(fact.id)
        else:
            query = """
                       UPDATE facts
                          SET end_time = ?
                        WHERE id = ?
            """
            self.execute(query, (end_time, fact.id))

    def _squeeze_in(self, start_time):
        """ tries to put task in the given date
            if there are conflicts, we will only truncate the ongoing task
            and replace it's end part with our activity """

        # we are checking if our start time is in the middle of anything
        # or maybe there is something after us - so we know to adjust end time
        # in the latter case go only few hours ahead. everything else is madness, heh
        query = """
                   SELECT a.*, b.name
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                    WHERE ((start_time < ? and end_time > ?)
                           OR (start_time > ? and start_time < ? and end_time is null)
                           OR (start_time > ? and start_time < ?))
                 ORDER BY start_time
                    LIMIT 1
                """
        row = self.fetchone(query, (start_time, start_time,
                                    start_time - dt.timedelta(hours = 12),
                                    start_time, start_time,
                                    start_time + dt.timedelta(hours = 12)))
        end_time = None
        if row:
            if start_time > row['start_time']:
                #we are in middle of a fact - truncate it to our start
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, row['id']))

            else: #otherwise we have found a task that is after us
                end_time = row['start_time']

        return end_time

    def _solve_overlaps(self, start_time, end_time):
        """finds facts that happen in given interval and shifts them to
        make room for new fact
        """
        if end_time is None or start_time is None:
            return

        # possible combinations and the OR clauses that catch them
        # (the side of the number marks if it catches the end or start time)
        #             |----------------- NEW -----------------|
        #      |--- old --- 1|   |2 --- old --- 1|   |2 --- old ---|
        # |3 -----------------------  big old   ------------------------ 3|
        query = """
                   SELECT a.*, b.name as activity, c.name as category
                     FROM facts a
                LEFT JOIN activities b on b.id = a.activity_id
                LEFT JOIN categories c on b.category_id = c.id
                    WHERE (end_time > ? and end_time < ?)
                       OR (start_time > ? and start_time < ?)
                       OR (start_time < ? and end_time > ?)
                 ORDER BY start_time
                """
        conflicts = self.fetchall(query, (start_time, end_time,
                                          start_time, end_time,
                                          start_time, end_time))

        for row in conflicts:
            fact = Fact(**row)
            fact_end_time = fact.end_time or hamster_now()

            # won't eliminate as it is better to have overlapping entries than loosing data
            if start_time < fact.start_time and end_time > fact_end_time:
                continue

            # split - truncate until beginning of new entry and create new activity for end
            if fact.start_time < start_time < fact_end_time and \
               fact.start_time < end_time < fact_end_time:

                logger.info("splitting %s" % fact)
                # truncate until beginning of the new entry
                self.execute("""UPDATE facts
                                   SET end_time = ?
                                 WHERE id = ?""", (start_time, fact.id))

                # create new fact for the end
                new_fact = fact.copy()
                new_fact.end_time = fact_end_time
                new_fact_id = self.add_fact(new_fact)

                # copy tags
                tag_update = """INSERT INTO fact_tags(fact_id, tag_id)
                                     SELECT ?, tag_id
                                       FROM fact_tags
                                      WHERE fact_id = ?"""
                self.execute(tag_update, (new_fact_id, fact.id)) #clone tags

            # overlap start
            elif start_time < fact.start_time < end_time:
                logger.info("Overlapping start of %s" % fact)
                self.execute("UPDATE facts SET start_time=? WHERE id=?",
                             (end_time, fact.id))

            # overlap end
            elif start_time < fact_end_time < end_time:
                logger.info("Overlapping end of %s" % fact)
                self.execute("UPDATE facts SET end_time=? WHERE id=?",
                             (start_time, fact.id))


    def add_fact(self, fact, temporary=False):

        logger.info("adding fact {}".format(fact))

        if not fact.activity or fact.start_time is None:  # sanity check
            return 0


        # get tags from database - this will create any missing tags too
        tags = [(tag['id'], tag['name'], tag['autocomplete'])
                for tag in self._get_tag_ids(fact.tags)[0]]

        # now check if maybe there is also a category
        category_id = None
        if fact.category:
            category_id = self.get_category_id(fact.category)
            if not category_id:
                category_id = self.add_category(fact.category)

        # try to find activity, resurrect if not temporary
        activity_id = self.get_activity_by_name(fact.activity,
                                                category_id,
                                                resurrect = not temporary)
        if not activity_id:
            activity_id = self.add_activity(fact.activity,
                                            category_id, temporary)
        else:
            activity_id = activity_id['id']

        # if we are working on +/- current day - check the last_activity
        start_time = fact.start_time
        if (dt.timedelta(days=-1) <= hamster_now() - start_time <= dt.timedelta(days=1)):
            # pull in previous facts
            facts = self.get_todays_facts()

            previous = None
            if facts and facts[-1].end_time == None:
                previous = facts[-1]

            if previous and previous.start_time <= start_time:
                # check if maybe that is the same one, in that case no need to restart
                if previous.activity_id == activity_id \
                   and set(previous.tags) == set([tag[1] for tag in tags]) \
                   and (previous.description or "") == (fact.description or ""):
                    return None

                # if no description is added
                # see if maybe previous was too short to qualify as an activity
                if not previous.description \
                   and 60 >= (start_time - previous.start_time).seconds >= 0:
                    self._remove_fact(previous.id)

                    # now that we removed the previous one, see if maybe the one
                    # before that is actually same as the one we want to start
                    # (glueing)
                    if len(facts) > 1 and 60 >= (start_time - facts[-2].end_time).seconds >= 0:
                        before = facts[-2]
                        if before.activity_id == activity_id \
                           and set(before.tags) == set([tag[1] for tag in tags]):
                            # resume and return
                            update = """
                                       UPDATE facts
                                          SET end_time = null
                                        WHERE id = ?
                            """
                            self.execute(update, (before.id,))

                            return before.id
                else:
                    # otherwise stop
                    update = """
                               UPDATE facts
                                  SET end_time = ?
                                WHERE id = ?
                    """
                    self.execute(update, (start_time, previous.id))


        # done with the current activity, now we can solve overlaps
        end_time = fact.end_time
        if not end_time:
            end_time = self._squeeze_in(start_time)
        else:
            self._solve_overlaps(start_time, end_time)


        # finally add the new entry
        insert = """
                    INSERT INTO facts (activity_id, start_time, end_time, description)
                               VALUES (?, ?, ?, ?)
        """
        self.execute(insert, (activity_id, start_time, end_time, fact.description))

        fact_id = self._last_insert_rowid()

        #now link tags
        insert = ["insert into fact_tags(fact_id, tag_id) values(?, ?)"] * len(tags)
        params = [(fact_id, tag[0]) for tag in tags]
        self.execute(insert, params)

        self._remove_index([fact_id])

        logger.info("fact successfully added, with id #{}".format(fact_id))
        return fact_id

    def _last_insert_rowid(self):
        return self.fetchone("SELECT last_insert_rowid();")[0]


    def get_todays_facts(self):
        """Gets facts of today, respecting hamster midnight. See GetFacts for
        return info"""
        return self.get_facts(hamster_today())


    def get_facts(self, date, end_date = None, search_terms = ""):
        split_time = conf.day_start
        start = dt.datetime.combine(date, split_time)

        end_date = end_date or date
        end = dt.datetime.combine(end_date, split_time) + dt.timedelta(days=1, seconds=-1)

        logger.info("searching for facts from %s to %s" % (start, end))

        query = """
                   SELECT a.id AS id,
                          a.start_time AS start_time,
                          a.end_time AS end_time,
                          a.description as description,
                          b.name AS activity, b.id as activity_id,
                          coalesce(c.name, ?) as category,
                          e.name as tag
                     FROM facts a
                LEFT JOIN activities b ON a.activity_id = b.id
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN fact_tags d ON d.fact_id = a.id
                LEFT JOIN tags e ON e.id = d.tag_id
                    WHERE (a.end_time >= ? OR a.end_time IS NULL) AND a.start_time <= ?
        """

        if search_terms:
            # check if we need changes to the index
            self._check_index(start, end)

            # flip the query around when it starts with "not "
            reverse_search_terms = search_terms.lower().startswith("not ")
            if reverse_search_terms:
                search_terms = search_terms[4:]

            search_terms = search_terms.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').replace("'", "''")
            query += """ AND a.id %s IN (SELECT id
                                         FROM fact_index
                                         WHERE fact_index MATCH '%s')""" % ('NOT' if reverse_search_terms else '',
                                                                            search_terms)

        query += " ORDER BY a.start_time, e.name"

        fact_dicts = self.fetchall(query, (self._unsorted, start, end))

        # put all tags in an array and convert to Fact instances
        facts = self._create_facts(fact_dicts)

        res = []
        for fact in facts:
            # heuristics to assign tasks to proper days

            # if fact has no end time, set the last minute of the day,
            # or current time if fact has happened in last 12 hours
            if fact.end_time:
                fact_end_time = fact.end_time
            elif (hamster_today() == fact.start_time.date()) or \
                 (hamster_now() - fact.start_time) <= dt.timedelta(hours=12):
                fact_end_time = hamster_now()
            else:
                fact_end_time = fact.start_time

            fact_start_date = fact.start_time.date() \
                - dt.timedelta(1 if fact.start_time.time() < split_time else 0)
            fact_end_date = fact_end_time.date() \
                - dt.timedelta(1 if fact_end_time.time() < split_time else 0)
            fact_date_span = fact_end_date - fact_start_date

            # check if the task spans across two dates
            if fact_date_span.days == 1:
                datetime_split = dt.datetime.combine(fact_end_date, split_time)
                start_date_duration = datetime_split - fact.start_time
                end_date_duration = fact_end_time - datetime_split
                if start_date_duration > end_date_duration:
                    # most of the task was done during the previous day
                    fact_date = fact_start_date
                else:
                    fact_date = fact_end_date
            else:
                # either doesn't span or more than 24 hrs tracked
                # (in which case we give up)
                fact_date = fact_start_date

            if fact.start_time < start - dt.timedelta(days=30):
                # ignoring old on-going facts
                continue

            fact.date = fact_date
            res.append(fact)

        return res

    def _remove_fact(self, fact_id):
        logger.info("removing fact #{}".format(fact_id))
        statements = ["DELETE FROM fact_tags where fact_id = ?",
                      "DELETE FROM facts where id = ?"]
        self.execute(statements, [(fact_id,)] * 2)

        self._remove_index([fact_id])

    def get_category_activities(self, category_id=(-1)):
        """returns list of activities, if category is specified, order by name
           otherwise - by activity_order"""
        query = """
                   SELECT a.id, a.name, a.category_id, b.name as category
                     FROM activities a
                LEFT JOIN categories b on coalesce(b.id, -1) = a.category_id
                    WHERE category_id = ?
                      AND deleted is null
                 ORDER BY lower(a.name)
        """

        return self.fetchall(query, (category_id, ))


    def get_activities(self, search=""):
        """returns list of activities for autocomplete,
           activity names converted to lowercase"""

        query = """
                   SELECT a.name AS name, b.name AS category
                     FROM activities a
                LEFT JOIN categories b ON coalesce(b.id, -1) = a.category_id
                LEFT JOIN facts f ON a.id = f.activity_id
                    WHERE deleted IS NULL
                      AND a.search_name LIKE ? ESCAPE '\\'
                 GROUP BY a.id
                 ORDER BY max(f.start_time) DESC, lower(a.name)
                    LIMIT 50
        """
        search = search.lower()
        search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        activities = self.fetchall(query, ('%s%%' % search, ))

        return activities

    def remove_activity(self, id):
        """ check if we have any facts with this activity and behave accordingly
            if there are facts - sets activity to deleted = True
            else, just remove it"""

        query = "select count(*) as count from facts where activity_id = ?"
        bound_facts = self.fetchone(query, (id,))['count']

        if bound_facts > 0:
            self.execute("UPDATE activities SET deleted = 1 WHERE id = ?", (id,))
        else:
            self.execute("delete from activities where id = ?", (id,))


    def remove_category(self, id):
        """move all activities to unsorted and remove category"""

        affected_query = """
            SELECT id
              FROM facts
             WHERE activity_id in (SELECT id FROM activities where category_id=?)
        """
        affected_ids = [res[0] for res in self.fetchall(affected_query, (id,))]

        update = "update activities set category_id = -1 where category_id = ?"
        self.execute(update, (id, ))

        self.execute("delete from categories where id = ?", (id, ))

        self._remove_index(affected_ids)


    def add_activity(self, name, category_id = None, temporary = False):
        # first check that we don't have anything like that yet
        activity = self.get_activity_by_name(name, category_id)
        if activity:
            return activity['id']

        #now do the create bit
        category_id = category_id or -1

        deleted = None
        if temporary:
            deleted = 1


        query = """
                   INSERT INTO activities (name, search_name, category_id, deleted)
                        VALUES (?, ?, ?, ?)
        """
        self.execute(query, (name, name.lower(), category_id, deleted))
        return self._last_insert_rowid()

    def _remove_index(self, ids):
        """remove affected ids from the index"""
        if not ids:
            return
        ids = ",".join((str(id) for id in ids))
        logger.info("removing fact #{} from index".format(ids))
        self.execute("DELETE FROM fact_index where id in (%s)" % ids)


    def _check_index(self, start, end):
        """check if maybe index needs rebuilding in the time span"""
        index_query = """SELECT id
                           FROM facts
                          WHERE (end_time >= ? OR end_time IS NULL)
                            AND start_time <= ?
                            AND id not in(select id from fact_index)"""

        rebuild_ids = ",".join([str(res[0]) for res in
                                self.fetchall(index_query, (start, end))])

        if rebuild_ids:
            query = """
                       SELECT a.id AS id,
                              a.start_time AS start_time,
                              a.end_time AS end_time,
                              a.description as description,
                              b.name AS activity, b.id as activity_id,
                              coalesce(c.name, ?) as category,
                              e.name as tag
                         FROM facts a
                    LEFT JOIN activities b ON a.activity_id = b.id
                    LEFT JOIN categories c ON b.category_id = c.id
                    LEFT JOIN fact_tags d ON d.fact_id = a.id
                    LEFT JOIN tags e ON e.id = d.tag_id
                        WHERE a.id in (%s)
                     ORDER BY a.id
            """ % rebuild_ids

            facts = self._create_facts(self.fetchall(query, (self._unsorted, )))

            insert = """INSERT INTO fact_index (id, name, category, description, tag)
                             VALUES (?, ?, ?, ?, ?)"""
            params = [(f.id, f.activity, f.category, f.description, ' '.join(f.tags))
                      for f in facts]

            self.executemany(insert, params)


    last_sql_msg, last_sql_count = "", 0

    def _log_debug(self, query, params):
        """
        Make compact version of query for debug logger.
        """
        if logger.level > logging.DEBUG: return

        msg = ' '.join((w.strip() for w in query.split()))[:200]
        msg += '...' if len(msg) > 200 else ''
        if params:
            msg += ' :: ' + ','.join((str(p) for p in params))
        msg = msg[:300] + (' ...' if len(msg) > 300 else '')
        if msg == self.last_sql_msg:
            self.last_sql_count += 1
        else:
            if self.last_sql_count:
                logger.debug("last db operation repeated %d time%s"
                             % (self.last_sql_count,
                                '' if self.last_sql_count == 1 else 's'))
            logger.debug(msg)
            self.last_sql_msg, self.last_sql_count = msg, 0
        return


    """ Here be dragons (lame connection/cursor wrappers) """
    @property
    def connection(self):
        if self.con is None:
            self.con = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            self.con.row_factory = sqlite3.Row

        return self.con


    def fetchall(self, query, params = None):
        con = self.connection
        cur = con.cursor()
        self._log_debug(query, params)
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        res = cur.fetchall()
        cur.close()

        return res

    def fetchone(self, query, params = None):
        self._log_debug(query, params)
        res = self.fetchall(query, params)
        if res:
            return res[0]
        else:
            return None

    def execute(self, statement, params=()):
        """
        execute sql statement. optionally you can give multiple statements
        to save on cursor creation and closure
        """
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        if isinstance(statement, list) == False: # we expect to receive instructions in list
            statement = [statement]
            params = [params]

        for state, param in zip(statement, params):
            self._log_debug(state, param)
            cur.execute(state, param)

        if not self.__con:
            con.commit()
            cur.close()

    def executemany(self, statement, params=[]):
        con = self.__con or self.connection
        cur = self.__cur or con.cursor()

        self._log_debug(statement, params)
        cur.executemany(statement, params)

        if not self.__con:
            con.commit()
            cur.close()



    def start_transaction(self):
        # will give some hints to execute not to close or commit anything
        self.__con = self.connection
        self.__cur = self.__con.cursor()

    def end_transaction(self):
        self.__con.commit()
        self.__cur.close()
        self.__con, self.__cur = None, None

    def run_fixtures(self):
        self.start_transaction()

        """upgrade DB to hamster version"""
        version = self.fetchone("SELECT version FROM version")["version"]
        logger.debug("database version is %s" % version)
        current_version = 9

        if version < 8:
            # working around sqlite's utf-f case sensitivity (bug 624438)
            # more info: http://www.gsak.net/help/hs23820.htm
            self.execute("ALTER TABLE activities ADD COLUMN search_name varchar2")

            activities = self.fetchall("select * from activities")
            statement = "update activities set search_name = ? where id = ?"
            for activity in activities:
                self.execute(statement, (activity['name'].lower(), activity['id']))

            # same for categories
            self.execute("ALTER TABLE categories ADD COLUMN search_name varchar2")
            categories = self.fetchall("select * from categories")
            statement = "update categories set search_name = ? where id = ?"
            for category in categories:
                self.execute(statement, (category['name'].lower(), category['id']))

        if version < 9:
            # adding full text search
            self.execute("""CREATE VIRTUAL TABLE fact_index
                                           USING fts3(id, name, category, description, tag)""")


        # at the happy end, update version number
        if version < current_version:
            #lock down current version
            self.execute("UPDATE version SET version = %d" % current_version)
            print("updated database from version %d to %d" % (version, current_version))

        self.end_transaction()
