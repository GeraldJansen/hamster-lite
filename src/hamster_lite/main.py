#!/usr/bin/env python3
# - coding: utf-8 -

# This file is part of 'hamster-lite'.

# 'hamster-lite' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Project Hamster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with 'hamster-lite'.  If not, see <http://www.gnu.org/licenses/>.

# This software is based heavily on Project Hamster
# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>.
# See https://github.com/projecthamster/hamster/graphs/contributors.
# It also borrows code from the `hamster-gtk` rewrite by
# https://github.com/projecthamster/hamster-gtk/blob/develop/AUTHORS.rst.

'''A script to control Hamster-lite time tracker from the command line.'''

import sys, os
import datetime as dt
import gi
gi.require_version('Gtk', '3.0')  # NOQA
from gi.repository import Gtk, GObject
from gi.repository import GLib as glib

from hamster_lite import reports
from hamster_lite import logger as hamster_logger
from hamster_lite.lib import default_logger, i18n
from hamster_lite.overview import Overview
from hamster_lite.fact_editor import FactEditor
from hamster_lite import storage

i18n.setup_i18n()

logger = default_logger(__file__)


class SignalHandler(GObject.GObject):
    """Simple signaling class to provide custom signal registration."""
    __gsignals__ = {
        str('facts-changed'): (GObject.SignalFlags.RUN_LAST, None, ()),
        str('activities-changed'): (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    def __init__(self):
        super().__init__()


class HamsterLite(Gtk.Application):
    """Main application class."""

    def __init__(self, name="overview"):
        """Setup instance and make sure default signals are connected to methods."""
        super().__init__(application_id='org.hamster-lite')

        self.signal = SignalHandler()

        self.connect('startup', self._startup)
        self.connect('activate', self._activate)
        self.connect('shutdown', self._shutdown)
        self.name = name
        self.window = None

    def _startup(self, app):
        """Triggered right at startup."""
        print(_("Hamster-lite started."))  # NOQA
        glib.set_application_name("Hamster-lite")
        self.db = storage.Storage()

    def _activate(self, app):
        """Triggered in regular use after startup."""
        if not self.window:
            if self.name == "edit":
                print('edit: argv', sys.argv)
                if sys.argv[-1] == 'edit':
                    self.window = FactEditor(app)
                else:
                    self.window = FactEditor(app, fact_id=int(sys.argv[-1]))
            else:
                self.window = Overview(app)

        app.add_window(self.window)
        self.window.show_all()
        self.window.present()

    def _shutdown(self, app):
        """Triggered upon termination."""
        print(_('Hamster-lite shut down.'))  # NOQA

    def _on_quit(self, action, parameter):
        """Callback for quit action."""
        self.quit()


if __name__ == '__main__':
    app = HamsterLite()
    app.run()
