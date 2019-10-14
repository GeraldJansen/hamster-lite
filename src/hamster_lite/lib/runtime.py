# -*- coding: utf-8 -*-

# Copyright (C) 2008, 2014 Toms Bauģis <toms.baugis at gmail.com>

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

import os
import json
import datetime as dt
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from xdg.BaseDirectory import xdg_data_home, xdg_config_home
import hamster_lite.storage as db


class Controller(gobject.GObject):
    __gsignals__ = {
        "on-close": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
        "facts-changed": (gobject.SignalFlags.RUN_LAST, gobject.TYPE_NONE, ()),
    }

    def __init__(self, parent=None, ui_file=""):
        gobject.GObject.__init__(self)

        self.parent = parent

        if ui_file:
            self._gui = load_ui_file(ui_file)
            self.window = self.get_widget('window')
        else:
            self._gui = None
            self.window = gtk.Window()

        self.window.connect("delete-event", self.window_delete_event)
        if self._gui:
            self._gui.connect_signals(self)


    def get_widget(self, name):
        """ skip one variable (huh) """
        return self._gui.get_object(name)


    def window_delete_event(self, widget, event):
        self.close_window()

    def close_window(self):
        if not self.parent:
            gtk.main_quit()
        else:
            self.window.destroy()
            self.window = None
            self.emit("on-close")

    def show(self):
        self.window.show()


def load_ui_file(name):
    """loads interface from the glade file; sorts out the path business"""
    ui = gtk.Builder()
    ui.add_from_file(os.path.join(runtime.data_dir, name))
    return ui



class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if '__instance' not in vars(cls):
            cls.__instance = object.__new__(cls, *args, **kwargs)
        return cls.__instance

class RuntimeStore(Singleton):
    """XXX - kill"""
    data_dir = ""
    home_data_dir = ""
    storage = None

    def __init__(self):
        try:
            from hamster_lite import defs
            self.data_dir = os.path.join(defs.DATA_DIR, "hamster-lite")
            self.version = defs.VERSION
        except:
            # if defs is not there, we are running from sources
            module_dir = os.path.dirname(os.path.realpath(__file__))
            self.data_dir = os.path.join(module_dir, '..', '..', '..', 'data')
            self.version = "uninstalled"

        self.data_dir = os.path.realpath(self.data_dir)
        self.storage = db.Storage()
        self.home_data_dir = os.path.realpath(
            os.path.join(xdg_data_home, "hamster-lite"))


runtime = RuntimeStore()


class OneWindow(object):
    def __init__(self, get_dialog_class):
        self.dialogs = {}
        self.get_dialog_class = get_dialog_class
        self.dialog_close_handlers = {}

    def on_close_window(self, dialog):
        for key, assoc_dialog in list(self.dialogs.items()):
            if dialog == assoc_dialog:
                del self.dialogs[key]

        handler = self.dialog_close_handlers.pop(dialog)
        dialog.disconnect(handler)


    def show(self, parent = None, **kwargs):
        params = str(sorted(kwargs.items())) #this is not too safe but will work for most cases

        if params in self.dialogs:
            window = self.dialogs[params].window
            self.dialogs[params].show()
            window.present()
        else:
            if parent:
                dialog = self.get_dialog_class()(parent, **kwargs)

                if isinstance(parent, gtk.Widget):
                    dialog.window.set_transient_for(parent.get_toplevel())

                if hasattr(dialog, "connect"):
                    self.dialog_close_handlers[dialog] = dialog.connect("on-close", self.on_close_window)
            else:
                dialog = self.get_dialog_class()(**kwargs)

                # no parent means we close on window close
                dialog.window.connect("destroy",
                                      lambda window, params: gtk.main_quit(),
                                      params)

            self.dialogs[params] = dialog

class Dialogs(Singleton):
    """makes sure that we have single instance open for windows where it makes
       sense"""
    def __init__(self):
        def get_edit_class():
            from hamster_lite.edit_activity import CustomFactController
            return CustomFactController
        self.edit = OneWindow(get_edit_class)

        def get_overview_class():
            from hamster_lite.overview import Overview
            return Overview
        self.overview = OneWindow(get_overview_class)

        def get_about_class():
            from hamster_lite.about import About
            return About
        self.about = OneWindow(get_about_class)

        def get_prefs_class():
            from hamster_lite.preferences import PreferencesEditor
            return PreferencesEditor
        self.prefs = OneWindow(get_prefs_class)

dialogs = Dialogs()
