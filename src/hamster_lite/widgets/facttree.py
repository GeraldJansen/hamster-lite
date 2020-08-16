# -*- coding: utf-8 -*-

# Copyright (C) 2020 Gerald Jansen <gjansen at ownmail dot net>

# This file is part of Hamster-lite.

# Hamster-lite is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Hamster-lite.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from hamster_lite.lib import hamster_now, format_duration, escape_pango
from hamster_lite.lib import word_wrap


def small(text):
    return f"<small>{escape_pango(text)}</small>"

def bold(text):
    #return f"<bold>{text}</bold>"
    return text


class FactTree(gtk.ScrolledWindow):
    """
    The fact tree does not change facts by itself, only sends signals.
    Facts get updated only through `set_facts`.
    """

    def __init__(self):

        super().__init__()
        self.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        self.props.border_width = 5

        self.store = gtk.ListStore(str, str, str, str, int)
        self.treeview = gtk.TreeView().new_with_model(self.store)
        col_titles = [(_('Date'), False),
                      (_('Start - End'), False),
                      (_('Activity'), True),
                      (_('Time'), False)]
        for i, (col_title, expand) in enumerate(col_titles):
            renderer = gtk.CellRendererText()
            col = gtk.TreeViewColumn(col_title, renderer, text=i)
            col.set_expand(expand)
            self.treeview.append_column(col)
        self.treeview.expand_all()
        self.add(self.treeview)

        self.current_iter = None
        self.current_fact = None

        select = self.treeview.get_selection()
        select.connect("changed", self._on_selection_changed)

    def _on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter:
            self.current_fact = self.facts[model[treeiter][-1]]
            #log.debug(f"Fact selected: {str(self.current_fact)}")
        else:
            self.current_fact = None

    def update_facts(self, facts):

        self.store.clear()
        if not facts:
            return
        self.facts = facts
        prev_date = None
        for idx, fact in enumerate(facts):
            if fact.date != prev_date:
                # show date on first fact of the day
                date = _("Today") if fact.date == hamster_now().date() \
                    else fact.date.strftime('%a %d %b %Y')
                prev_date = fact.date
            else:
                date = ''
            start_end = fact.start_time.strftime('%H:%M - ')
            if fact.end_time:
                start_end += fact.end_time.strftime('%H:%M')
            activity = escape_pango(fact.activity)
            if fact.category:
                activity += ' - ' + escape_pango(fact.category)
            if fact.description:
                activity += ', ' + fact.description
            activity = '\n'.join(word_wrap(activity, 72))
            if fact.tags:
                activity += ' ' + ', '.join(
                    ['#' + tag for tag in fact.tags])
            time = format_duration(
                (fact.end_time or hamster_now()) - fact.start_time)
            self.store.append([date, start_end, activity, time, idx])
        self.treeview.expand_all()
        self.treeview.show()
