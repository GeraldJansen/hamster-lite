# - coding: utf-8 -

# Copyright (C) 2008-2009 Toms Bauģis <toms.baugis at gmail.com>

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

import logging
logger = logging.getLogger(__name__)   # noqa: E402

import bisect
import cairo
import datetime as dt
import re

from gi.repository import Gdk as gdk
from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
import gi
gi.require_version('PangoCairo', '1.0')
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
from collections import defaultdict
from copy import deepcopy

from hamster.lib import Fact, looks_like_time
from hamster.lib import stuff
from hamster.lib import graphics
import hamster.storage as db

def extract_search(text):
    fact = Fact.parse(text)
    search = fact.activity
    if fact.category:
        search += "@%s" % fact.category
    if fact.tags:
        search += " #%s" % (" #".join(fact.tags))
    return search

class DataRow(object):
    """want to split out visible label, description, activity data
      and activity data with time (full_data)"""
    def __init__(self, label, data=None, full_data=None, description=None):
        self.label = label
        self.data = data or label
        self.full_data = full_data or data or label
        self.description = description or ""

class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y
        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        self.height = self.layout.get_pixel_size()[1]

    def show(self, g, text, color=None):
        g.move_to(self.x, self.y)

        self.layout.set_markup(text)
        g.save_context()
        if color:
            g.set_color(color)
        pangocairo.show_layout(g.context, self.layout)
        g.restore_context()


class CompleteTree(graphics.Scene):
    """
    ASCII Art

    | Icon | Activity - description |

    """

    __gsignals__ = {
        # enter or double-click, passes in current day and fact
        'on-select-row': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }


    def __init__(self):
        graphics.Scene.__init__(self, style_class=gtk.STYLE_CLASS_VIEW)

        self.set_can_focus(False)

        self.row_positions = []

        self.current_row = None
        self.rows = []

        self.style = self._style

        self.label = Label(x=5, y=3)
        self.row_height = self.label.height + 10

        self.connect("on-key-press", self.on_key_press)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)

    def _get_mouse_row(self, event):
        hover_row = None
        for row, y in zip(self.rows, self.row_positions):
            if y <= event.y <= (y + self.row_height):
                hover_row = row
                break
        return hover_row

    def on_mouse_move(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.current_row = row
            self.redraw()

    def on_mouse_down(self, scene, event):
        row = self._get_mouse_row(event)
        if row:
            self.set_current_row(self.rows.index(row))

    def on_key_press(self, scene, event):
        if event.keyval == gdk.KEY_Up:
            idx = self.rows.index(self.current_row) if self.current_row else 1
            self.set_current_row(idx - 1)

        elif event.keyval == gdk.KEY_Down:
            idx = self.rows.index(self.current_row) if self.current_row else -1
            self.set_current_row(idx + 1)

    def set_current_row(self, idx):
        idx = max(0, min(len(self.rows) - 1, idx))
        row = self.rows[idx]
        self.current_row = row
        self.redraw()
        self.emit("on-select-row", row)

    def set_rows(self, rows):
        self.current_row = None
        self.rows = rows
        self.set_row_positions()

    def set_row_positions(self):
        """creates a list of row positions for simpler manipulation"""
        self.row_positions = [i * self.row_height for i in range(len(self.rows))]
        self.set_size_request(0, self.row_positions[-1] + self.row_height if self.row_positions else 0)

    def on_enter_frame(self, scene, context):
        if not self.height:
            return

        colors = {
            "normal": self.style.get_color(gtk.StateFlags.NORMAL),
            "normal_bg": self.style.get_background_color(gtk.StateFlags.NORMAL),
            "selected": self.style.get_color(gtk.StateFlags.SELECTED),
            "selected_bg": self.style.get_background_color(gtk.StateFlags.SELECTED),
        }

        g = graphics.Graphics(context)
        g.set_line_style(1)
        g.translate(0.5, 0.5)


        for row, y in zip(self.rows, self.row_positions):
            g.save_context()
            g.translate(0, y)

            color, bg = colors["normal"], colors["normal_bg"]
            if row == self.current_row:
                color, bg = colors["selected"], colors["selected_bg"]
                g.fill_area(0, 0, self.width, self.row_height, bg)

            label = row.label
            if row.description:
                description_color = graphics.Colors.mix(bg, color, 0.75)
                description_color_str = graphics.Colors.hex(description_color)

                label = '{}  <span color="{}">[{}]</span>'.format(label,
                                                                  description_color_str,
                                                                  row.description)

            self.label.show(g, label, color=color)

            g.restore_context()



class ActivityEntry(gtk.Entry):
    def __init__(self, updating=True, **kwargs):
        gtk.Entry.__init__(self)

        # to be set by the caller, if editing an existing fact
        self.original_fact = None

        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        box = gtk.Frame()
        box.set_shadow_type(gtk.ShadowType.IN)
        self.popup.add(box)

        self.complete_tree = CompleteTree()
        self.tree_checker = self.complete_tree.connect("on-select-row", self.on_tree_select_row)
        self.complete_tree.connect("on-click", self.on_tree_click)
        box.add(self.complete_tree)

        self.storage = db.Storage()
        self.load_suggestions()
        self.ignore_stroke = False

        self.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY, "go-down-symbolic")

        self.checker = self.connect("changed", self.on_changed)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("icon-press", self.on_icon_press)



    def on_changed(self, entry):
        text = self.get_text()

        with self.complete_tree.handler_block(self.tree_checker):
            self.show_suggestions(text)

        if self.ignore_stroke:
            self.ignore_stroke = False
            return

        def complete():
            text, suffix = self.complete_first()
            if suffix:
                #self.ignore_stroke = True
                with self.handler_block(self.checker):
                    self.update_entry("%s%s" % (text, suffix))
                    self.select_region(len(text), -1)
        gobject.timeout_add(0, complete)

    def on_focus_out(self, entry, event):
        self.popup.hide()

    def on_icon_press(self, entry, icon, event):
        if self.popup.get_visible():
            self.popup.hide()
        else:
            self.show_suggestions(self.get_text())

    def on_key_press(self, entry, event=None):
        if event.keyval in (gdk.KEY_BackSpace, gdk.KEY_Delete):
            self.ignore_stroke = True

        elif event.keyval in (gdk.KEY_Return, gdk.KEY_Escape):
            self.popup.hide()
            self.set_position(-1)

        elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down):
            if not self.popup.get_visible():
                self.show_suggestions(self.get_text())
            self.complete_tree.on_key_press(self, event)
            return True

    def on_tree_click(self, entry, tree, event):
        self.popup.hide()

    def on_tree_select_row(self, tree, row):
        with self.handler_block(self.checker):
            label = row.full_data
            self.update_entry(label)
            self.set_position(-1)


    def load_suggestions(self):
        self.todays_facts = self.storage.get_todays_facts()

        # list of facts of last month
        now = stuff.hamster_now()
        last_month = self.storage.get_facts(now - dt.timedelta(days=30), now)

        # naive recency and frequency rank
        # score is as simple as you get 30-days_ago points for each occurence
        suggestions = defaultdict(int)
        for fact in last_month:
            days = 30 - (now - fact.start_time).days
            label = fact.activity
            if fact.category:
                label += "@%s" % fact.category

            suggestions[label] += days

            if fact.tags:
                label += " #%s" % (" #".join(fact.tags))
                suggestions[label] += days

        for rec in self.storage.get_activities():
            label = rec["name"]
            if rec["category"]:
                label += "@%s" % rec["category"]
            suggestions[label] += 0

        # list of (label, score), higher scores first
        self.suggestions = sorted(suggestions.items(), key=lambda x: x[1], reverse=True)

    def complete_first(self):
        text = self.get_text()
        fact = Fact.parse(text)
        search = extract_search(text)
        if not self.complete_tree.rows or not fact.activity:
            return text, None

        label = self.complete_tree.rows[0].data
        if label.startswith(search):
            return text, label[len(search):]

        return text, None


    def update_entry(self, text):
        self.set_text(text or "")


    def update_suggestions(self, text=""):
        """
            * from previous activity | set time | minutes ago | start now
            * to ongoing | set time

            * activity
            * [@category]
            * #tags, #tags, #tags

            * we will leave description for later

            all our magic is space separated, strictly, start-end can be just dash

            phases:

            [start_time] | [-end_time] | activity | [@category] | [#tag]
        """

        res = []

        fact = Fact.parse(text)
        now = stuff.hamster_now()

        # figure out what we are looking for
        # time -> activity[@category] -> tags -> description
        # presence of an attribute means that we are not looking for the previous one
        # we still might be looking for the current one though
        looking_for = "start_time"
        fields = ["start_time", "end_time", "activity", "category", "tags", "description", "done"]
        for field in reversed(fields):
            if getattr(fact, field, None):
                looking_for = field
                if text[-1] == " ":
                    looking_for = fields[fields.index(field)+1]
                break


        fragments = [f for f in re.split("[\s|#]", text)]
        current_fragment = fragments[-1] if fragments else ""


        search = extract_search(text)

        matches = []
        for match, score in self.suggestions:
            if search in match:
                if match.startswith(search):
                    score += 10**8 # boost beginnings
                matches.append((match, score))

        # need to limit these guys, sorry
        matches = sorted(matches, key=lambda x: x[1], reverse=True)[:7]

        for match, score in matches:
            label = (fact.start_time or now).strftime("%H:%M")
            if fact.end_time:
                label += fact.end_time.strftime("-%H:%M")

            markup_label = label + " " + (stuff.escape_pango(match).replace(search, "<b>%s</b>" % search) if search else match)
            label += " " + match

            res.append(DataRow(markup_label, match, label))

        # list of tuples (description, variant)
        variants = []

        if self.original_fact:
            # editing an existing fact

            variant_fact = None
            if self.original_fact.end_time is None:
                description = "stop now"
                variant_fact = self.original_fact.copy()
                variant_fact.end_time = now
            elif self.original_fact == self.todays_facts[-1]:
                # that one is too dangerous, except for the last entry
                description = "keep up"
                # Do not use Fact(..., end_time=None): it would be a no-op
                variant_fact = self.original_fact.copy()
                variant_fact.end_time = None

            if variant_fact:
                variant_fact.description = None
                variant = variant_fact.serialized(prepend_date=False)
                variants.append((description, variant))

        else:
            # brand new fact
            description = "start now"
            variant = now.strftime("%H:%M ")
            variants.append((description, variant))

            prev_fact = self.todays_facts[-1] if self.todays_facts else None
            if prev_fact and prev_fact.end_time:
                since = stuff.format_duration(now - prev_fact.end_time)
                description = "from previous activity, %s ago" % since
                variant = prev_fact.end_time.strftime("%H:%M ")
                variants.append((description, variant))

            description = "start activity -n minutes ago (1 or 3 digits allowed)"
            variant = "-"
            variants.append((description, variant))

        text = text.strip()
        if text:
            description = "clear"
            variant = ""
            variants.append((description, variant))

        for (description, variant) in variants:
            res.append(DataRow(variant, description=description))

        self.complete_tree.set_rows(res)


    def show_suggestions(self, text):
        if not self.get_window():
            return

        entry_alloc = self.get_allocation()
        entry_x, entry_y = self.get_window().get_origin()[1:]
        x, y = entry_x + entry_alloc.x, entry_y + entry_alloc.y + entry_alloc.height

        self.popup.show_all()

        self.update_suggestions(text)

        tree_w, tree_h = self.complete_tree.get_size_request()

        self.popup.move(x, y)
        self.popup.resize(entry_alloc.width, tree_h)
        self.popup.show_all()
