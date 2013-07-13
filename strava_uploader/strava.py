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

from __future__ import absolute_import

import json
import urllib2

import cStringIO as StringIO

from . import mechanize



_URL_LOGIN = 'https://www.strava.com/login'
_URL_UPLOAD = 'http://app.strava.com/upload/select'
_URL_UPLOAD_STATUS = 'http://app.strava.com/upload/progress.json?' \
        'new_uploader=true'

class StravaError(urllib2.URLError):
    pass




def _open_url(browser, url):

    try:
        browser.open(url)
    except mechanize.HTTPError as e:
        raise StravaError(str(e))

def _get_response(browser):
    try:
        return json.loads(browser.response().get_data())
    except ValueError, e:
        raise StravaError('Failed to parse JSON response')


class StravaUploader(object):

    def __init__(self):

        self.browser = mechanize.Browser()
        self.authenticated = False


    def authenticate(self, email, password):

        _open_url(self.browser, _URL_LOGIN)

        try:
            self.browser.select_form(
                predicate=lambda f: 'id' in f.attrs and \
                f.attrs['id'] == 'login_form')
        except mechanize.FormNotFoundError as e:
            raise StravaError('Login form not found')

        self.browser['email'] = email
        self.browser['password'] = password

        try:
            self.browser.submit()
        except mechanize.HTTPError as e:
            raise StravaError(str(e))

        if self.browser.geturl() == _URL_LOGIN:
            raise StravaError('Failed to authenticate')

        self.authenticated = True


    def upload(self, tracks):

        _open_url(self.browser, _URL_UPLOAD)

        try:
            self.browser.select_form(
                predicate=lambda f: 'action' in f.attrs and \
                f.attrs['action'] == '/upload/files')
        except mechanize.FormNotFoundError as e:
            raise StravaError('Upload form not found')


        for filename, data in tracks:
            self.browser.form.add_file(StringIO.StringIO(data),
                                       'application/octet-stream',
                                       filename, name='files[]')


        try:
            self.browser.submit()
        except mechanize.HTTPError as e:
            raise StravaError(str(e))

        resp = _get_response(self.browser)

        if len(resp) != len(tracks):
            raise StravaError('Unexpected response')


        return UploadStatus(self.browser, resp)






class UploadStatus(object):

    def __init__(self, browser, uploads):
        self.browser = browser
        self.uploads = uploads

        self.finished = False
        self.status_msg = ''



    def check_progress(self):

        _open_url(self.browser, self._statusUrl())


        resp = _get_response(self.browser)

        if len(resp) != len(self.uploads):
            raise StravaError('Unexpected response')

        finished = True
        for u in resp:
            if u['progress'] != 100 and ('error' not in u):
                finished = False

        return finished, resp



    def _statusUrl(self):

        ids = []
        for t in self.uploads:
            ids.append('ids[]=%s' % t['id'])

        return _URL_UPLOAD_STATUS + '&' + '&'.join(ids)

