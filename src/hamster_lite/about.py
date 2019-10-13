# -*- coding: utf-8 -*-

# Copyright (C) 2007, 2008 Toms Bauģis <toms.baugis at gmail.com>

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


from os.path import join
from hamster_lite.lib.runtime import runtime
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk

class About(object):
    def __init__(self, parent = None):
        about = gtk.AboutDialog()
        self.window = about
        infos = {
            "program-name" : _("Time Tracker"),
            "name" : _("Time Tracker"), #this should be deprecated in gtk 2.10
            "version" : runtime.version,
            "comments" : _("Project Hamster — track your time"),
            "copyright" : _("Copyright © 2007–2010 Toms Bauģis and others"),
            "website" : "http://projecthamster.wordpress.com/",
            "website-label" : _("Project Hamster Website"),
            "title": _("About Time Tracker"),
            "wrap-license": True
        }

        about.set_authors(["Toms Bauģis <toms.baugis@gmail.com>",
                           "Patryk Zawadzki <patrys@pld-linux.org>",
                           "Pēteris Caune <cuu508@gmail.com>",
                           "Juanje Ojeda <jojeda@emergya.es>"])
        about.set_artists(["Kalle Persson <kalle@kallepersson.se>"])

        about.set_translator_credits(_("translator-credits"))

        for prop, val in infos.items():
            about.set_property(prop, val)

        about.set_logo_icon_name("hamster-lite")

        about.connect("response", lambda self, *args: self.destroy())
        about.show_all()
