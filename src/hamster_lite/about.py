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
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
import hamster_lite

class About(gtk.AboutDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        infos = {
            "program-name" : _("Hamster-lite Time Tracker"),
            "version" : hamster_lite.__version__,
            "comments" : _("Your personal time keeping tool"),
            "copyright" : _("Copyright © 2019-2020 Gerald Jansen"),
            "website" : "https://github.com/GeraldJansen/hamster-lite/wiki/",
            "website-label" : _("Hamster-lite Github Wiki"),
            "title": _("About Hamster-lite"),
            "wrap-license": True
        }

        self.set_authors(["Gerald Jansen <gjansen@ownmail.net>",
                           "Toms Bauģis <toms.baugis@gmail.com>",
                           "Patryk Zawadzki <patrys@pld-linux.org>",
                           "Pēteris Caune <cuu508@gmail.com>",
                           "Juanje Ojeda <jojeda@emergya.es>"])
        self.set_artists(["Kalle Persson <kalle@kallepersson.se>"])

        self.set_translator_credits(_("translator-credits"))

        for prop, val in infos.items():
            self.set_property(prop, val)

        self.set_logo_icon_name("hamster-lite")

        self.connect("response", lambda self, *args: self.destroy())
        self.show_all()
