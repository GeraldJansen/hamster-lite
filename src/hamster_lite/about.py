# -*- coding: utf-8 -*-

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
# Copyright (C) 2007-2009 Toms Bauģis <toms.baugis at gmail.com>,
# https://github.com/projecthamster/hamster.
# It also borrows code from the `hamster-gtk` rewrite by
# https://github.com/projecthamster/hamster-gtk/blob/develop/AUTHORS.rst.


from os.path import join
from hamster_lite.lib.runtime import runtime
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk

class About(object):
    def __init__(self, parent = None):
        about = gtk.AboutDialog()
        self.window = about
        infos = {
            "program-name" : _("Hamster-lite Time Tracker"),
            "version" : runtime.version,
            "comments" : _("Your personal time keeping tool"),
            "copyright" : _("Copyright © 2019 Gerald Jansen"),
            "website" : "https://github.com/GeraldJansen/hamster-lite/wiki/",
            "website-label" : _("Hamster-lite Github Wiki"),
            "title": _("About Hamster-lite"),
            "wrap-license": True
        }

        about.set_authors(["Gerald Jansen <gjansen@ownmail.net>",
                           "Toms Bauģis <toms.baugis@gmail.com>",
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
