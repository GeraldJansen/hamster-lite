# -*- coding: utf-8 -*-

# Copyright (C) 2020 Gerald Jansen <gjansen@ownmail.net>
# Copyright (C) 2007-2009, 2014 Toms Bauģis <toms.baugis at gmail.com>

# This file is part of Hamster-lite (a fork of Project Hamster).

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

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
import datetime as dt

from hamster_lite import widgets
from hamster_lite.lib.configuration import conf
from hamster_lite.lib.stuff import (
    hamsterday_time_to_datetime, hamster_today, hamster_now)
from hamster_lite.lib import Fact, parse_fact


class FactEditor(gtk.Window):

    def __init__(self, app=None, parent=None, fact_id=None, base_fact=None):
        super().__init__(title=_("Edit activity"),
                         border_width=12,
                         icon_name='hamster-lite')

        self._app = app

        self.set_size_request(500, 1)
        self.parent = parent

        # None if creating a new fact, instead of editing one
        self.fact_id = fact_id

        self.date = hamster_today()

        mainbox = gtk.Box(spacing=6, orientation='vertical', can_focus=False)
        self.add(mainbox)

        self.cmdline = widgets.CmdLineEntry()
        box1 = gtk.Box(orientation='vertical', can_focus=False)
        label = gtk.Label(xalign=0.)
        label.set_markup('<b><i>%s</i></b>' % _('Activity@Category'))
        box1.pack_start(label, 0, 0, 0)
        box1.pack_start(self.cmdline, 0, 1, 0)
        mainbox.pack_start(box1, 0, 1, 0)

        self.date_button = gtk.Button(str(hamster_today()))
        self.date_button.connect('clicked', self.on_date_button_clicked)
        self.date_popover = gtk.Popover()
        cal = gtk.Calendar()
        cal.connect("day-selected", self.on_day_selected)
        self.date_popover.add(cal)

        self.start_time = widgets.TimeInput()
        self.end_time = widgets.TimeInput()

        box2 = gtk.Box(orientation='horizontal', can_focus=False)
        box2.pack_start(self.date_button, 1, 1, 0)
        box2.pack_start(gtk.Label(_('Start')), 1, 1, 0)
        box2.pack_start(self.start_time, 1, 1, 0)
        box2.pack_start(gtk.Label(_('End')), 1, 1, 0)
        box2.pack_start(self.end_time, 1, 1, 0)
        mainbox.pack_start(box2, 0, 1, 0)

        box3 = gtk.Box(orientation='vertical', can_focus=False)
        box3win = gtk.ScrolledWindow(
            visible=True, can_focus=True, shadow_type="in",
            hscrollbar_policy="never")
        self.description = gtk.TextView(
            height_request=50, visible=True, can_focus=True,
            wrap_mode="word-char", accepts_tab=False)
        self.description_buffer = self.description.get_buffer()
        box3win.add(self.description)
        label = gtk.Label(xalign=0.)
        label.set_markup('<b><i>%s</i></b>' % _('Description'))
        box3.pack_start(label, 0, 0, 0)
        box3.pack_start(box3win, 1, 1, 0)
        mainbox.pack_start(box3, 1, 1, 0)

        self.tags_entry = widgets.TagsEntry()
        box4 = gtk.Box(orientation='vertical', can_focus=False)
        label = gtk.Label(xalign=0.)
        label.set_markup('<b><i>%s</i></b>' % _('Tags'))
        box4.pack_start(label, 0, 0, 0)
        box4.pack_start(self.tags_entry, 0, 1, 0)
        mainbox.pack_start(box4, 0, 1, 0)

        self.delete_button = gtk.Button(_('Delete'))
        self.cancel_button = gtk.Button(_('Cancel'))
        self.save_button = gtk.Button(_('Save'))
        self.delete_button.connect('clicked', self.on_delete_clicked)
        self.cancel_button.connect('clicked', self.on_cancel_clicked)
        self.save_button.connect('clicked', self.on_save_clicked)

        lastbox = gtk.Box(orientation='horizontal', spacing=8, can_focus=False)
        lastbox.pack_start(self.delete_button, 0, 1, 0)
        lastbox.pack_end(self.save_button, 0, 0, 0)
        lastbox.pack_end(self.cancel_button, 0, 1, 0)

        mainbox.pack_start(lastbox, 0, 1, 0)

        # this will set self.master_is_cmdline
        self.cmdline.grab_focus()

        if fact_id:
            # editing
            self.fact = self._app.db.get_fact(fact_id)
            self.date = self.fact.date
            self.set_title(_("Update activity"))
        else:
            self.set_title(_("Add activity"))
            self.date = hamster_today()
            self.delete_button.set_sensitive(False)
            if base_fact:
                # start a clone now.
                self.fact = base_fact.copy(start_time=hamster_now(),
                                           end_time=None)
            else:
                self.fact = Fact(start_time=hamster_now())

        self.update_fields()
        self.update_cmdline()

        # This signal should be emitted only after a manual modification,
        # not at init time when cmdline might not always be fully parsable.
        self.cmdline.connect("changed", self.on_cmdline_changed)

        self.cmdline.connect("focus_in_event", self.on_cmdline_focus_in_event)
        self.cmdline.connect("focus_out_event", self.on_cmdline_focus_out_event)
        self.description_buffer.connect("changed", self.on_description_changed)
        self.start_time.connect("changed", self.on_start_time_changed)
        self.end_time.connect("changed", self.on_end_time_changed)
        self.tags_entry.connect("changed", self.on_tags_changed)

        self.connect("key-press-event", self.on_window_key_pressed)

        self.validate_fields()
        self.show_all()

    def show(self):
        self.show()


    def on_cmdline_focus_in_event(self, widget, event):
        pass

    def on_cmdline_focus_out_event(self, widget, event):
        self.update_fields()
        self.update_cmdline()

    def on_cmdline_changed(self, widget):
        fact_dict = parse_fact(self.cmdline.get_text(), date=self.date)
        update = False
        for key, value in fact_dict.items():
            if value and value != getattr(self.fact, key):
                setattr(self.fact, key, value)
                update = True
        if update:
            self.update_fields()

    def on_description_changed(self, text):
        buf = self.description_buffer
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), 0)
        self.fact.description = text.strip()
        self.validate_fields()

    def on_date_button_clicked(self, button):
        self.date_popover.set_relative_to(button)
        self.date_popover.show_all()
        self.date_popover.popup()

    def on_day_selected(self, calendar):
        date = calendar.get_date()
        self.date = dt.date(date.year, date.month + 1, date.day)
        self.date_button.set_label(str(self.date))
        self.date_popover.hide()
        if self.fact.start_time:
            delta = self.date - self.fact.start_time.date()
            self.fact.start_time += delta
            if self.fact.end_time:
                # preserve fact duration
                self.fact.end_time += delta
        self.validate_fields()

    def on_start_time_changed(self, widget):
        # note: resist the temptation to preserve duration here;
        # for instance, end time might be at the beginning of next fact.
        new_time = self.start_time.time
        if new_time:
            if self.fact.start_time:
                new_start_time = dt.datetime.combine(self.fact.start_time.date(),
                                                     new_time)
            else:
                # date not specified; result must fall in current hamster_day
                new_start_time = hamsterday_time_to_datetime(hamster_today(),
                                                             new_time)
        else:
            new_start_time = None
        self.fact.start_time = new_start_time
        # let start_date extract date or handle None
        #self.start_date.date = new_start_time
        self.validate_fields()

    def on_end_time_changed(self, widget):
        # self.end_time.start_time() was given a datetime,
        # so self.end_time.time is a datetime too.
        end = self.end_time.time
        self.fact.end_time = end
        self.validate_fields()

    def on_tags_changed(self, widget):
        self.fact.tags = self.tags_entry.get_tags()

    def update_cmdline(self):
        """Update the cmdline entry content."""
        label = self.fact.activity or ""
        if self.fact.category:
            label += '@' + self.fact.category
        with self.cmdline.handler_block(self.cmdline.checker):
            self.cmdline.set_text(label)

    def update_fields(self):
        """Update gui fields content."""
        if self.fact.start_time:
            self.date = self.fact.start_time.date()
            self.start_time.time = self.fact.start_time
        if self.fact.end_time:
            self.end_time.time = self.fact.end_time
            self.end_time.set_start_time(self.fact.start_time)
        if self.fact.description:
            self.description_buffer.set_text(self.fact.description)
        if self.fact.tags:
            self.tags_entry.set_tags(self.fact.tags)
        self.validate_fields()

    def update_status(self, status, markup):
        """Set save button sensitivity and tooltip."""
        self.save_button.set_tooltip_markup(markup)
        if status == "okay":
            self.save_button.set_label(_('Save'))
            self.save_button.set_sensitive(True)
        elif status == "warning":
            self.save_button.set_label(_('Warning'))
            self.save_button.set_sensitive(True)
        elif status == "wrong":
            self.save_button.set_label(_('Save'))
            self.save_button.set_sensitive(False)
        else:
            raise ValueError("unknown status: '{}'".format(status))

    def validate_fields(self):
        """Check for start_time and activity entries."""
        if not self.fact.activity:
            self.update_status(status="wrong", markup=_("Missing activity"))
            return None
        self.update_status(status="okay", markup="")
        return True

    def on_delete_clicked(self, button):
        self._app.db.remove_fact(self.fact_id)
        self.close_window()

    def on_cancel_clicked(self, button):
        self.close_window()

    def on_close(self, widget, event):
        self.close_window()

    def on_save_clicked(self, button):
        if self.fact_id:
            self._app.db.update_fact(self.fact_id, self.fact)
        else:
            self._app.db.add_fact(self.fact)
        self.close_window()

    def on_window_key_pressed(self, tree, event_key):
        popups = (self.cmdline.popup.get_property("visible")
                  or self.start_time.popup.get_property("visible")
                  or self.end_time.popup.get_property("visible")
                  or self.tags_entry.popup.get_property("visible"))
        #or self.date_popover.get_property("visible")

        if (event_key.keyval == gdk.KEY_Escape or \
           (event_key.keyval == gdk.KEY_w and event_key.state & gdk.ModifierType.CONTROL_MASK)):
            if popups:
                return False

            self.close_window()

        elif event_key.keyval in (gdk.KEY_Return, gdk.KEY_KP_Enter):
            if popups:
                return False
            if self.description.has_focus():
                return False
            if self.validate_fields():
                self.on_save_clicked(None)

    def close_window(self):
        self._gui = None
        self.destroy()
