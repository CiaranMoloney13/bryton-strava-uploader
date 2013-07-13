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


import urlparse
import urllib
import urllib2
import json
import errno
import shutil
import tempfile
import os
import time

from PyQt4.QtCore import QObject, pyqtSignal, QTimer

from .strava import StravaUploader, StravaError


BASE_BB_URL = 'http://127.0.0.1:18888'


SUPPORTED_VERSIONS = ['2.6.0.8']


class BBClient(QObject):

    deviceOffline = pyqtSignal()
    tracksReady = pyqtSignal(list)
    error = pyqtSignal(str)
    unsupportedBBVersion = pyqtSignal(str)


    uploadStatus = pyqtSignal(str)
    stravaCredentialsNeeded = pyqtSignal()
    stravaUploadStarted = pyqtSignal(list)
    stravaUploadProgress = pyqtSignal(list)
    stravaUploadFinished = pyqtSignal(list)



    def __init__(self, parent=None, strava_username=None,
                 strava_password=None, bb_url=BASE_BB_URL):

        super(BBClient, self).__init__(parent)
        self._bb_url = bb_url

        self._connected = False
        self._first_run = True
        self._status_timer = None

        self._strava_username = strava_username
        self._strava_password = strava_password

        self._tracks = []
        self._exp_tracks = []


    def _onThreadStart(self):

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._checkStatus)
        self._strava = StravaUploader()

        self.error.connect(self._onError)


    def _onError(self):
        self._status_timer.stop()
        self._connected = False
        self._first_run = True
        self._tracks = []
        self._exp_tracks = []


    def onAbortUpload(self):

        self._exp_tracks = []




    def onUploadTracks(self, track_ids):

        self._track_ids = track_ids

        if not self._exp_tracks:
            self.uploadStatus.emit('Exporting tracks')
            self._exp_tracks = self._exportTracks(track_ids)


        if not self._strava.authenticated:

            self.uploadStatus.emit('Authenticating to Strava')
            if not self._strava_username:
                self.stravaCredentialsNeeded.emit()
                return

            try:
                self._strava.authenticate(self._strava_username,
                                          self._strava_password)
            except StravaError as e:
                self._strava_username = ''
                self.uploadStatus.emit('Retrying authenticating to Strava')
                self.stravaCredentialsNeeded.emit()
                return


        tracks = self._exp_tracks
        self._exp_tracks = []

        self.uploadStatus.emit(
            'Uploading to strava<br>(Can sometimes be a little slow)')
        try:
            status = self._strava.upload(tracks)
        except StravaError as e:
            self.error.emit(e.reason)
            return

        self.stravaUploadStarted.emit(status.uploads)

        while True:

            time.sleep(2)

            finished, progress = status.check_progress()

            if not finished:
                self.stravaUploadProgress.emit(progress)
            else:
                self.stravaUploadFinished.emit(progress)
                return




    def onStravaCredentials(self, username, password):
        self._strava_username = username
        self._strava_password = password

        self.onUploadTracks(self._track_ids)

    def onClearStravaCredentials(self):
        self._strava_username = None
        self._strava_password = None
        if self._strava.authenticated:
            self._strava = StravaUploader()


    def onStart(self):
        if self._status_timer is not None:
            self._status_timer.start(1000)
        else:
            QTimer.singleShot(1000, self.onStart)



    def _checkStatus(self):

        info = self._bbRequest('/device/info')
        if info is None:
            return

        if info['connected']:
            if not self._connected and 'Device' in info:
                self._connected = True
                self._status_timer.setInterval(6000)
                self.tracksReady.emit(info['Device']['tracks'])
                self._tracks = info['Device']['tracks']

                if 'BB' in info and 'version' in info['BB']:
                    if info['BB']['version'] not in SUPPORTED_VERSIONS:
                        self.unsupportedBBVersion.emit(info['BB']['version'])

        else:
            if self._connected or self._first_run:
                self._connected = False
                self._status_timer.setInterval(3000)
                self.deviceOffline.emit()


        if self._first_run and self._status_timer.interval() == 1000:
            self._status_timer.setInterval(3000)

        self._first_run = False



    def _exportTracks(self, ids):

        if not self._tracks:
            return []

        tmp_path = tempfile.mkdtemp()

        resp = self._bbRequest('/device/do/export', fmt='tcx',
                               list=','.join(map(str, ids)),
                               num=len(self._tracks), dest=tmp_path)

        content = []

        if resp is not None and 'ok' in resp and resp['ok']:

            names = os.listdir(tmp_path)

            if len(names) == len(ids):

                matches = self._matchNames(ids, names)

                if matches is None:
                    self.error.emit('Failed to export tracks')
                else:
                    for name in matches:
                        with open(os.path.join(tmp_path, name)) as f:
                            content.append((name, f.read()))

            else:
                self.error.emit('Failed to export tracks')

        shutil.rmtree(tmp_path)

        return content




    def _matchNames(self, ids, filenames):

        ret = []

        for i, fname in zip(ids, filenames):

            name = self._tracks[i]

            name = name.replace('/', '').replace(' ', '').replace(':', '')

            if fname.startswith(name):
                ret.append(fname)

        if len(ret) == len(filenames):
            return ret

        ret = []

        fnames = filenames[:]

        for i in ids:

            name = self._tracks[i]

            name = name.replace('/', '').replace(' ', '').replace(':', '')

            for fname in fnames:
                if fname.startswith(name):
                    ret.append(fname)
                    fnames.remove(fname)
                    break

        if len(ret) == len(filenames):
            return ret

        return None


    def _bbRequest(self, path, **args):

        url = urlparse.urljoin(self._bb_url, path)

        if args:
            url += '?' + urllib.urlencode(args)

        error = 'Unknown network error'
        try:
            req = urllib2.urlopen(url)
            return json.loads(req.read())

        except urllib2.URLError as e:
            if e.reason.errno == errno.ECONNREFUSED:
                error = 'Failed to connect to BrytonBridge'
        except urllib.HTTPError as e:
            if e.reason == 'Not Found':
                error = 'Unknown network error'
        else:
            pass

        self.error.emit(error)






