# -*- coding: utf-8 -*-

# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

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

import sys
import bisect
import datetime as dt
import itertools
import webbrowser

from collections import defaultdict
from math import ceil

from gi.repository import Gio as gio
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

import gi
gi.require_version('PangoCairo', '1.0')
from gi.repository import PangoCairo as pangocairo
from gi.repository import Pango as pango
import cairo

from hamster_lite import widgets, reports
from hamster_lite.lib import graphics, layout, stuff
from hamster_lite.lib.runtime import dialogs, Controller
from hamster_lite.lib.configuration import conf
from hamster_lite.lib.pytweener import Easing
from hamster_lite.widgets.dates import RangePick
from hamster_lite.widgets.facttree import FactTree
from hamster_lite.about import About

class HeaderBar(gtk.HeaderBar):
    def __init__(self):
        gtk.HeaderBar.__init__(self)
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


class StackedBar(layout.Widget):
    def __init__(self, width=0, height=0, vertical=None, **kwargs):
        layout.Widget.__init__(self, **kwargs)

        #: orientation, horizontal by default
        self.vertical = vertical or False

        #: allocated width
        self.width = width

        #: allocated height
        self.height = height

        self._items = []
        self.connect("on-render", self.on_render)

        #: color scheme to use, graphics.colors.category10 by default
        self.colors = graphics.Colors.category10
        self.colors = ["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"]

        self._seen_keys = []


    def set_items(self, items):
        """expects a list of key, value to work with"""
        res = []
        max_value = max(sum((rec[1] for rec in items)), 1)
        for key, val in items:
            res.append((key, val, val * 1.0 / max_value))
        self._items = res


    def _take_color(self, key):
        if key in self._seen_keys:
            index = self._seen_keys.index(key)
        else:
            self._seen_keys.append(key)
            index = len(self._seen_keys) - 1
        return self.colors[index % len(self.colors)]


    def on_render(self, sprite):
        if not self._items:
            self.graphics.clear()
            return

        max_width = self.alloc_w - 1 * len(self._items)
        for i, (key, val, normalized) in enumerate(self._items):
            color = self._take_color(key)

            width = int(normalized * max_width)
            self.graphics.rectangle(0, 0, width, self.height)
            self.graphics.fill(color)
            self.graphics.translate(width + 1, 0)


class Label(object):
    """a much cheaper label that would be suitable for cellrenderer"""
    def __init__(self, x=0, y=0, color=None, use_markup=False):
        self.x = x
        self.y = y
        self.color = color
        self.use_markup = use_markup

    def _set_text(self, text):
        if self.use_markup:
            self.layout.set_markup(text)
        else:
            self.layout.set_text(text, -1)

    def _show(self, g):
        if self.color:
            g.set_color(self.color)
        pangocairo.show_layout(g.context, self.layout)

    def show(self, g, text, x=0, y=0):
        g.save_context()
        g.move_to(x or self.x, y or self.y)
        self._set_text(text)
        self._show(g)
        g.restore_context()


class HorizontalBarChart(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.x_align = 0
        self.y_align = 0
        self.values = []

        self._label_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
        self.layout = pangocairo.create_layout(self._label_context)
        self.layout.set_font_description(pango.FontDescription(graphics._font_desc))
        self.layout.set_markup("Hamster") # dummy
        # ellipsize the middle because depending on the use case,
        # the distinctive information can be either at the beginning or the end.
        self.layout.set_ellipsize(pango.EllipsizeMode.MIDDLE)
        self.layout.set_justify(True)
        self.layout.set_alignment(pango.Alignment.RIGHT)
        self.label_height = self.layout.get_pixel_size()[1]
        self.label_color = gdk.RGBA()
        self.bar_color = gdk.RGBA()

        self._max = dt.timedelta(0)

    def set_values(self, values):
        """expects a list of 2-tuples"""
        self.values = values
        self.height = len(self.values) * 14
        self._max = max(rec[1] for rec in values) if values else dt.timedelta(0)

    def _draw(self, context, opacity, matrix):
        g = graphics.Graphics(context)
        g.save_context()
        g.translate(self.x, self.y)
        # arbitrary 3/4 total width for label, 1/4 for histogram
        hist_width = self.alloc_w // 4;
        margin = 10  # pixels
        label_width = self.alloc_w - hist_width - margin
        self.layout.set_width(label_width * pango.SCALE)
        label_h = self.label_height
        bar_start_x = label_width + margin
        for i, (label, value) in enumerate(self.values):
            g.set_color(self.label_color)
            duration_str = stuff.format_duration(value, human=False)
            markup_label = stuff.escape_pango(str(label))
            markup_duration = stuff.escape_pango(duration_str)
            self.layout.set_markup("{}, <i>{}</i>".format(markup_label, markup_duration))
            y = int(i * label_h * 1.5)
            g.move_to(0, y)
            pangocairo.show_layout(context, self.layout)
            if self._max > dt.timedelta(0):
                w = ceil(hist_width * value.total_seconds() /
                         self._max.total_seconds())
            else:
                w = 1
            g.rectangle(bar_start_x, y, int(w), int(label_h))
            g.fill(self.bar_color)

        g.restore_context()



class Totals(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_size_request(200, 70)
        self.category_totals = layout.Label(overflow=pango.EllipsizeMode.END,
                                            x_align=0,
                                            expand=False)
        self.stacked_bar = StackedBar(height=25, x_align=0, expand=False)

        box = layout.VBox(padding=10, spacing=5)
        self.add_child(box)

        box.add_child(self.category_totals, self.stacked_bar)

        self.totals = {}
        self.mouse_cursor = gdk.CursorType.HAND2

        self.instructions_label = layout.Label(_("Click to see stats"),
                                               color=self._style.get_color(gtk.StateFlags.NORMAL),
                                               padding=10,
                                               expand=False)

        box.add_child(self.instructions_label)
        self.collapsed = True

        main = layout.HBox(padding_top=10)
        box.add_child(main)

        self.stub_label = layout.Label(markup="<b>Here be stats,\ntune in laters!</b>",
                                       color="#bbb",
                                       size=60)

        self.activities_chart = HorizontalBarChart()
        self.categories_chart = HorizontalBarChart()
        self.tag_chart = HorizontalBarChart()

        main.add_child(self.activities_chart, self.categories_chart, self.tag_chart)




        # for use in animation
        self.height_proxy = graphics.Sprite(x=0)
        self.height_proxy.height = 70
        self.add_child(self.height_proxy)

        self.connect("on-click", self.on_click)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.connect("state-flags-changed", self.on_state_flags_changed)
        self.connect("style-updated", self.on_style_changed)


    def set_facts(self, facts):
        totals = defaultdict(lambda: defaultdict(dt.timedelta))
        for fact in facts:
            end_time = fact.end_time or stuff.hamster_now()
            delta = end_time - fact.start_time
            totals['category'][fact.category] += delta
            totals['activity'][fact.activity] += delta
            for tag in fact.tags:
                totals['tag'][tag] += delta

        for key, group in totals.items():
            totals[key] = sorted(group.items(), key=lambda x: x[1], reverse=True)
        self.totals = totals

        self.activities_chart.set_values(totals['activity'])
        self.categories_chart.set_values(totals['category'])
        self.tag_chart.set_values(totals['tag'])

        self.stacked_bar.set_items([(cat, delta.total_seconds() / 60.0) for cat, delta in totals['category']])

        grand_total = sum(delta.total_seconds() / 60
                          for __, delta in totals['activity'])
        self.category_totals.markup = "<b>Total: </b>%s; " % stuff.format_duration(grand_total)
        self.category_totals.markup += ", ".join("<b>%s:</b> %s" % (stuff.escape_pango(cat), stuff.format_duration(hours)) for cat, hours in totals['category'])



    def on_click(self, scene, sprite, event):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.change_height(70)
            self.instructions_label.visible = True
            self.instructions_label.opacity = 0
            self.instructions_label.animate(opacity=1, easing=Easing.Expo.ease_in)
        else:
            self.change_height(300)
            self.instructions_label.visible = False

        self.mouse_cursor = gdk.CursorType.HAND2 if self.collapsed else None

    def on_mouse_enter(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(100)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())


    def on_mouse_leave(self, scene, event):
        if not self.collapsed:
            return

        def delayed_leave(sprite):
            self.change_height(70)

        self.height_proxy.animate(x=50, delay=0.5, duration=0,
                                  on_complete=delayed_leave,
                                  on_update=lambda sprite: sprite.redraw())

    def on_state_flags_changed(self, previous_state, _):
        self.update_colors()

    def on_style_changed(self, _):
        self.update_colors()

    def change_height(self, new_height):
        self.stop_animation(self.height_proxy)
        def on_update_dummy(sprite):
            self.set_size_request(200, sprite.height)

        self.animate(self.height_proxy,
                     height=new_height,
                     on_update=on_update_dummy,
                     easing=Easing.Expo.ease_out)

    def update_colors(self):
        color = self._style.get_color(self.get_state())
        self.instructions_label.color = color
        self.category_totals.color = color
        self.activities_chart.label_color = color
        self.categories_chart.label_color = color
        self.tag_chart.label_color = color
        bg_color = self._style.get_background_color(self.get_state())
        bar_color = self.colors.mix(bg_color, color, 0.6)
        self.activities_chart.bar_color = bar_color
        self.categories_chart.bar_color = bar_color
        self.tag_chart.bar_color = bar_color


class Overview(gtk.ApplicationWindow):
    def __init__(self, app=None, *args, **kwargs):
        """Initialize overview."""
        super().__init__(*args, **kwargs)

        self._app = app
        self._app.signal.connect("facts-changed", self.on_facts_changed)
        self._app.signal.connect("activities-changed", self.on_facts_changed)
        def on_db_file_changed(monitor, gio_file, event_uri, event):
            if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
                self.find_facts()

        self.__db_file = gio.File.new_for_path(self._app.db.db_path)
        self.__db_monitor = self.__db_file.monitor_file\
            (gio.FileMonitorFlags.WATCH_MOUNTS, None)
        self.__db_monitor.connect("changed", on_db_file_changed)

        self.set_position(gtk.WindowPosition.CENTER)
        self.set_default_icon_name("hamster-lite")
        self.set_default_size(700, 500)

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


        window = gtk.ScrolledWindow()
        window.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        self.fact_tree = FactTree()
        self.fact_tree.connect("on-activate-row", self.on_row_activated)
        self.fact_tree.connect("on-delete-called", self.on_row_delete_called)

        window.add(self.fact_tree)
        main.pack_start(window, True, True, 1)

        self.totals = Totals()
        main.pack_start(self.totals, False, True, 1)

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
                              gdk.KEY_Page_Up, gdk.KEY_Page_Down,
                              gdk.KEY_Delete):
            # These keys should work even when fact_tree does not have focus
            self.fact_tree.on_key_press(self, event)
            return True  # stop event propagation
        elif event.keyval == gdk.KEY_Return:
            self.start_new_fact(clone_selected=True, fallback=False)
            return True
        elif event.keyval == gdk.KEY_Left:
            self.header_bar.time_back.emit("clicked")
            return True
        elif event.keyval == gdk.KEY_Right:
            self.header_bar.time_forth.emit("clicked")
            return True

        if self.fact_tree.has_focus() or self.totals.has_focus():
            if event.keyval == gdk.KEY_Tab:
                pass # TODO - deal with tab as our scenes eat up navigation

        if event.state & gdk.ModifierType.CONTROL_MASK:
            # the ctrl+things
            if event.keyval == gdk.KEY_f:
                self.header_bar.search_button.set_active(True)
            if event.keyval in (gdk.KEY_e, gdk.KEY_Return):
                self.fact_tree.on_key_press(self, event)
                return True
            elif event.keyval == gdk.KEY_n:
                self.start_new_fact(clone_selected=False)
            elif event.keyval == gdk.KEY_r:
                # Resume/run; clear separation between Ctrl-R and Ctrl-N
                self.start_new_fact(clone_selected=True, fallback=False)
            elif event.keyval == gdk.KEY_space:
                self._app.db.stop_tracking()
            elif event.keyval in (gdk.KEY_KP_Add, gdk.KEY_plus):
                # same as pressing the + icon
                self.start_new_fact(clone_selected=True, fallback=True)

        if event.keyval == gdk.KEY_Escape:
            if conf.get('escape_quits_main'):
                self._app.quit()

    def find_facts(self):
        start, end = self.header_bar.range_pick.get_range()
        search_active = self.header_bar.search_button.get_active()
        search = "" if not search_active else self.filter_entry.get_text()
        search = "%s*" % search if search else "" # search anywhere
        self.facts = self._app.db.get_facts(start, end, search_terms=search)
        self.fact_tree.set_facts(self.facts)
        self.totals.set_facts(self.facts)
        self.header_bar.stop_button.set_sensitive(
            self.facts and not self.facts[-1].end_time)
        self.show_all()

    def on_range_selected(self, button, range_type, start, end):
        self.find_facts()

    def on_search_changed(self, entry):
        if entry.get_text():
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      "edit-clear-symbolic")
        else:
            self.filter_entry.set_icon_from_icon_name(gtk.EntryIconPosition.SECONDARY,
                                                      None)
        self.find_facts()

    def on_search_icon_press(self, entry, position, event):
        if position == gtk.EntryIconPosition.SECONDARY:
            self.filter_entry.set_text("")

    def on_facts_changed(self, event):
        self.find_facts()

    def on_add_clicked(self, button):
        self.start_new_fact(clone_selected=True, fallback=True)
        self.find_facts()

    def on_stop_clicked(self, button):
        self._app.db.stop_tracking()
        self.find_facts()

    def on_row_activated(self, tree, day, fact):
        dialogs.edit.show(self, fact_id=fact.id)
        self.find_facts()

    def on_row_delete_called(self, tree, fact):
        self._app.db.remove_fact(fact.id)
        self.find_facts()

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
        uri = "https://geraldjansen.github.io/hamster-doc"
        try:
            gtk.show_uri(None, uri, gdk.CURRENT_TIME)
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
        if self.report_chooser:
            self.report_chooser.present()
            return

        start, end = self.header_bar.range_pick.get_range()

        def on_report_chosen(widget, format, path):
            self.report_chooser = None
            reports.simple(self.facts, start, end, format, path)

            if format == ("html"):
                webbrowser.open_new("file://%s" % path)
            else:
                try:
                    gtk.show_uri(None, "file://%s" % path, gdk.CURRENT_TIME)
                except:
                    pass # bug 626656 - no use in capturing this one i think

        def on_report_chooser_closed(widget):
            self.report_chooser = None


        self.report_chooser = widgets.ReportChooserDialog()
        self.report_chooser.connect("report-chosen", on_report_chosen)
        self.report_chooser.connect("report-chooser-closed", on_report_chooser_closed)
        self.report_chooser.show(start, end)

    def start_new_fact(self, clone_selected=True, fallback=True):
        """Start now a new fact.
        clone_selected (bool): whether to start a clone of currently
            selected fact or to create a new fact from scratch.
        fallback (bool): if True, fall back to creating from scratch
                         in case of no selected fact.
        """
        if not clone_selected:
            dialogs.edit.show(self, base_fact=None)
        elif self.fact_tree.current_fact or fallback:
            dialogs.edit.show(self, base_fact=self.fact_tree.current_fact)
        self.find_facts()
