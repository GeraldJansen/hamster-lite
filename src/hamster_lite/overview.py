# -*- coding: utf-8 -*-

# Portions copyright (C) 2019-2020 Gerald Jansen <gjansen at ownmail.net>
# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Hamster-lite.

# Project Hamster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Hamster-lite.  If not, see <http://www.gnu.org/licenses/>.

import datetime as dt
import webbrowser

from collections import defaultdict

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango

from hamster_lite import widgets, reports
from hamster_lite.lib import stuff
from hamster_lite.lib.runtime import dialogs
from hamster_lite.lib.configuration import conf
from hamster_lite.widgets.dates import RangePick
from hamster_lite.widgets.facttree import FactTree
from hamster_lite.about import About


class HeaderBar(gtk.HeaderBar):
    def __init__(self):
        gtk.HeaderBar.__init__(self, spacing=1)
        self.set_show_close_button(True)

        box = gtk.Box(False)
        self.time_back = gtk.Button.new_from_icon_name(
            "go-previous-symbolic", gtk.IconSize.MENU)
        self.time_forth = gtk.Button.new_from_icon_name(
            "go-next-symbolic", gtk.IconSize.MENU)

        box.add(self.time_back)
        box.add(self.time_forth)
        gtk.StyleContext.add_class(box.get_style_context(), "linked")
        self.pack_start(box)

        self.range_pick = RangePick(stuff.hamster_today())
        self.pack_start(self.range_pick)

        self.system_button = gtk.MenuButton()
        self.system_button.set_image(gtk.Image.new_from_icon_name(
            "open-menu-symbolic", gtk.IconSize.MENU))
        self.system_button.set_tooltip_markup(_("Menu"))
        self.pack_end(self.system_button)

        self.search_button = gtk.ToggleButton()
        self.search_button.set_image(gtk.Image.new_from_icon_name(
            "edit-find-symbolic", gtk.IconSize.MENU))
        self.search_button.set_tooltip_markup(_("Filter activities"))
        self.pack_end(self.search_button)

        self.stop_button = gtk.Button()
        self.stop_button.set_image(gtk.Image.new_from_icon_name(
            "process-stop-symbolic", gtk.IconSize.MENU))
        self.stop_button.set_tooltip_markup(_("Stop tracking (Ctrl-SPACE)"))
        self.pack_end(self.stop_button)

        self.add_button = gtk.Button()
        self.add_button.set_image(gtk.Image.new_from_icon_name(
            "list-add-symbolic", gtk.IconSize.MENU))
        self.add_button.set_tooltip_markup(_("Add activity (Ctrl-+)"))
        self.pack_end(self.add_button)

        self.system_menu = gtk.Menu()
        self.system_button.set_popup(self.system_menu)
        self.menu_export = gtk.MenuItem(label=_("Export..."))
        self.system_menu.append(self.menu_export)
        self.menu_prefs = gtk.MenuItem(label=_("Tracking Settings"))
        self.system_menu.append(self.menu_prefs)
        self.menu_help = gtk.MenuItem(label=_("Help"))
        self.system_menu.append(self.menu_help)
        self.menu_about = gtk.MenuItem(label=_("About"))
        self.system_menu.append(self.menu_about)
        self.system_menu.show_all()

        self.time_back.connect("clicked", self.on_time_back_click)
        self.time_forth.connect("clicked", self.on_time_forth_click)
        self.connect("button-press-event", self.on_button_press)

    def on_button_press(self, bar, event):
        """swallow clicks on the interactive parts to avoid triggering
        switch to full-window"""
        return True

    def on_time_back_click(self, button):
        self.range_pick.prev_range()

    def on_time_forth_click(self, button):
        self.range_pick.next_range()


class Totals(gtk.Label):
    def __init__(self):
        super().__init__()

    def update_totals(self, facts):
        grand_total = dt.timedelta(minutes=0)
        sub_totals = defaultdict(dt.timedelta)
        for fact in facts:
            end_time = fact.end_time or stuff.hamster_now()
            delta = end_time - fact.start_time
            grand_total += delta
            sub_totals[fact.category] += delta
        if facts:
            line = f"<b>Total </b> " \
                f"{stuff.format_duration(grand_total, human=False)}"
        else:
            line = "No activities to display. Use <b>+</b> to add an activity"
        if len(sub_totals) > 1:
            line += "  "
            line += '; '.join((f"{key or 'N/C'} "
                               f"{stuff.format_duration(val, human=False)}"
                               for key, val in sorted(sub_totals.items(),
                                                      key=lambda x: x[1],
                                                      reverse=True)))
        self.set_markup(line)
        self.set_ellipsize(pango.EllipsizeMode.END)


class Overview(gtk.ApplicationWindow):
    def __init__(self, app=None, *args, **kwargs):
        """Initialize overview."""
        super().__init__(*args, **kwargs)

        self._app = app
        self._app.db.connect("facts-changed", self.on_facts_changed)
        #self._app.signal.connect("facts-changed", self.on_facts_changed)
        #self._app.signal.connect("activities-changed", self.on_facts_changed)

        self.set_position(gtk.WindowPosition.CENTER)
        self.set_default_icon_name("hamster-lite")
        self.set_default_size(600, 400)

        self.header_bar = HeaderBar()
        self.set_titlebar(self.header_bar)

        main = gtk.Box(orientation=1)
        self.add(main)

        self.report_chooser = None

        self.search_box = gtk.Revealer()

        space = gtk.Box(border_width=5)
        self.search_box.add(space)
        self.filter_entry = gtk.Entry()
        self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.PRIMARY,
                                                  "edit-find-symbolic")
        self.filter_entry.connect("changed", self.on_search_changed)
        self.filter_entry.connect("icon-press", self.on_search_icon_press)

        space.pack_start(self.filter_entry, True, True, 0)
        main.pack_start(self.search_box, False, True, 0)

        self.fact_tree = FactTree()
        main.pack_start(self.fact_tree, True, True, 1)

        self.totals = Totals()
        main.pack_start(self.totals, False, False, 1)

        hamster_day = stuff.datetime_to_hamsterday(dt.datetime.today())
        self.header_bar.range_pick.set_range(hamster_day)
        self.header_bar.range_pick.connect("range-selected", self.on_range_selected)
        self.header_bar.add_button.connect("clicked", self.on_add_clicked)
        self.header_bar.stop_button.connect("clicked", self.on_stop_clicked)
        self.header_bar.search_button.connect("toggled", self.on_search_toggled)

        self.header_bar.menu_prefs.connect("activate", self.on_prefs_clicked)
        self.header_bar.menu_export.connect("activate", self.on_export_clicked)
        self.header_bar.menu_help.connect("activate", self.on_help_clicked)
        self.header_bar.menu_about.connect("activate", self.on_about_clicked)


        self.connect("key-press-event", self.on_key_press)

        self.facts = []
        self.find_facts()

        # update every minute (necessary if an activity is running)
        gobject.timeout_add_seconds(60, self.on_timeout)
        self.show_all()

    def on_key_press(self, window, event):
        if self.filter_entry.has_focus():
            if event.keyval == gdk.KEY_Escape:
                self.filter_entry.set_text("")
                self.header_bar.search_button.set_active(False)
                return True
        elif event.keyval in (gdk.KEY_Up, gdk.KEY_Down,
                              gdk.KEY_Home, gdk.KEY_End,
                              gdk.KEY_Page_Up, gdk.KEY_Page_Down):
            # TODO: fact_tree need to get focus ....
            # self.fact_tree.on_key_press(event)
            # return True  # stop event propagation
            pass
        elif event.keyval == gdk.KEY_Left:
            self.header_bar.time_back.emit("clicked")
            return True
        elif event.keyval == gdk.KEY_Right:
            self.header_bar.time_forth.emit("clicked")
            return True

        if self.fact_tree.has_focus():
            if event.keyval == gdk.KEY_Tab:
                pass # TODO - deal with tab as our scenes eat up navigation

        if event.state & gdk.ModifierType.CONTROL_MASK:
            # the ctrl+things
            if event.keyval in (gdk.KEY_e, gdk.KEY_Return):
                self. edit_selected_fact()
                return True
            if event.keyval == gdk.KEY_f:
                self.header_bar.search_button.set_active(True)
            elif event.keyval == gdk.KEY_space:
                self._app.db.stop_tracking()
            elif event.keyval == gdk.KEY_n:
                self.start_new_fact(clone_selected=False)
            elif event.keyval == gdk.KEY_r:
                # Resume/run; clear separation between Ctrl-R and Ctrl-N
                self.start_new_fact(clone_selected=True, fallback=False)
            elif event.keyval in (gdk.KEY_KP_Add, gdk.KEY_plus):
                # same as pressing the + icon
                self.start_new_fact(clone_selected=True, fallback=True)

        elif event.keyval == gdk.KEY_Delete:
            # delete fact uncerimoniously
            self.delete_selected_fact()
            return True
        elif event.keyval == gdk.KEY_Return:
            # resume selected fact directly, without editing
            base_fact = self.fact_tree.current_fact
            if base_fact:
                self._app.db.add_fact(
                    base_fact.copy(start_time=stuff.hamster_now(),
                                   end_time=None))
            return True

        if event.keyval == gdk.KEY_Escape:
            if conf.get('escape_quits_main'):
                self._app.quit()

    def edit_selected_fact(self):
        if self.fact_tree.current_fact:
            fact_id = self.fact_tree.current_fact.id
            dialogs.edit.show(self, db=self._app.db, fact_id=fact_id)

    def delete_selected_fact(self):
        if self.fact_tree.current_fact:
            fact_id = self.fact_tree.current_fact.id
            self._app.db.remove_fact(fact_id)

    def find_facts(self):
        start, end = self.header_bar.range_pick.get_range()
        search_active = self.header_bar.search_button.get_active()
        search = "" if not search_active else self.filter_entry.get_text()
        search = "%s*" % search if search else "" # search anywhere
        self.facts = self._app.db.get_facts(start, end, search_terms=search)
        self.fact_tree.update_facts(self.facts)
        self.totals.update_totals(self.facts)
        self.header_bar.stop_button.set_sensitive(
            self.facts and not self.facts[-1].end_time)
        self.show_all()

    def on_range_selected(self, button, range_type, start, end):
        self.find_facts()

    def on_search_changed(self, entry):
        if entry.get_text():
            self.filter_entry.set_icon_from_icon_name(
                gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic")
        else:
            self.filter_entry.set_icon_from_icon_name(
                gtk.EntryIconPosition.SECONDARY, None)
        self.find_facts()

    def on_search_icon_press(self, entry, position, event):
        if position == gtk.EntryIconPosition.SECONDARY:
            self.filter_entry.set_text("")

    def on_facts_changed(self, event):
        self.find_facts()

    def on_add_clicked(self, button):
        self.start_new_fact(clone_selected=True, fallback=True)

    def on_stop_clicked(self, button):
        self._app.db.stop_tracking()

    def on_search_toggled(self, button):
        active = button.get_active()
        self.search_box.set_reveal_child(active)
        if active:
            self.filter_entry.grab_focus()

    def on_timeout(self):
        # TODO: should update only the running FactTree row (if any), and totals
        self.find_facts()
        # The timeout will stop if returning False
        return True

    def on_help_clicked(self, menu):
        uri = "https://geraldjansen.github.io/hamster-lite"
        try:
            webbrowser.open(uri)
        except gi.repository.GLib.Error:
            dialog = gtk.MessageDialog(self, 0, gtk.MessageType.ERROR,
                                       gtk.ButtonsType.CLOSE,
                                       _("Failed to open {}").format(uri))
            dialog.run()
            dialog.destroy()

    def on_about_clicked(self, menu):
        dialog = About()
        dialog.run()
        dialog.destroy()

    def on_prefs_clicked(self, menu):
        dialogs.prefs.show(self)

    def on_export_clicked(self, menu):
        if not self.facts:
            msg = _("No activities to report in this time period.")
            dialog = gtk.MessageDialog(self, 0, gtk.MessageType.ERROR,
                                       gtk.ButtonsType.CLOSE, msg)
            dialog.run()
            dialog.destroy()
            return

        if self.report_chooser:
            self.report_chooser.present()
            return

        start, end = self.header_bar.range_pick.get_range()

        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, start, end, format, path)

            if format == ("html"):
                webbrowser.open("file://%s" % path)
            else:
                try:
                    gtk.show_uri(None, "file://%s" % path, gdk.CURRENT_TIME)
                except:
                    pass # bug 626656 - no use in capturing this one i think

        def on_report_chooser_closed(widget):
            self.report_chooser = None

        self.report_chooser = widgets.ReportChooserDialog()
        self.report_chooser.connect("report-chosen", on_report_chosen)
        self.report_chooser.connect("report-chooser-closed",
                                    on_report_chooser_closed)
        self.report_chooser.show(start, end)

    def start_new_fact(self, clone_selected=True, fallback=True):
        """Start now a new fact.
        clone_selected (bool): whether to start a clone of currently
            selected fact or to create a new fact from scratch.
        fallback (bool): if True, fall back to creating from scratch
                         in case of no selected fact.
        """
        if not clone_selected:
            dialogs.edit.show(self, db=self._app.db, base_fact=None)
        elif self.fact_tree.current_fact or fallback:
            dialogs.edit.show(self, db=self._app.db,
                              base_fact=self.fact_tree.current_fact)
