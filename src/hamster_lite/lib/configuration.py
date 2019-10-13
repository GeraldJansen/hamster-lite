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
from xdg.BaseDirectory import xdg_data_home, xdg_config_home


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if '__instance' not in vars(cls):
            cls.__instance = object.__new__(cls, *args, **kwargs)
        return cls.__instance

class ConfStore(Singleton):
    """
    Settings implementation which stores settings as json string in hamster.db
    """
    DEFAULTS = {
        'enable_timeout'              :   False,       # Should hamster stop tracking on idle
        'stop_on_shutdown'            :   False,       # Should hamster stop tracking on shutdown
        'notify_interval'             :   27,          # Remind of current activity every X minutes
        'day_start_minutes'           :   5 * 60 + 30, # At what time does the day start (5:30AM)
        'activities_source'           :   "",          # Source of TODO items ("", "evo", "gtg")
        'last_report_folder'          :   "~",         # Path to directory where the last report was saved
    }

    def __init__(self):
        self.config = self.DEFAULTS
        config_dir = os.path.join(xdg_config_home, 'hamster-lite')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        self.config_file = os.path.join(config_dir, 'hamster-lite.json')
        if os.path.exists(self.config_file):
            self._load_config()
        else:
            self._save_config()

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, sort_keys=True, indent=4)

    def _load_config(self):
        with open(self.config_file, 'r') as f:
            self.config.update(json.load(f))

    def get(self, key):
        """
        Returns the value of the conf key
        """
        # for now, update from config file every time (ugh)
        # - later update config only on external file change
        self._load_config()

        if key not in self.config:
            logger.warn("Unknown config key: %s" % key)
            return None
        else:
            return self.config[key]

    def set(self, key, value):
        """
        Set the key value and save config file
        """
        logger.info("Settings %s -> %s" % (key, value))

        self.config[key] = value
        self._save_config()

        return True

    @property
    def day_start(self):
        """Start of the hamster day."""
        day_start_minutes = self.config["day_start_minutes"]
        hours, minutes = divmod(day_start_minutes, 60)
        return dt.time(hours, minutes)

conf = ConfStore()
