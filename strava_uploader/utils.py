#
# Copyright (C) 2013  Per Myren
#
# This file is part of Bryton-Strava-Uploader
#
# Bryton-Strava-Uploader is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bryton-Strava-Uploader is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bryton-Strava-Uploader.
# If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os



if getattr(sys, 'frozen', None):
     _basedir = sys._MEIPASS
else:
     _basedir = os.path.dirname(__file__)


def resource_path(name):

    return os.path.join(_basedir, name)

