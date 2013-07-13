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
import math

from PyQt4.QtCore import Qt, QThread, QTimer, QSize, pyqtSignal, QSettings
from PyQt4.QtGui import (
    QApplication, QIcon, QWidget,
    QVBoxLayout, QHBoxLayout, QPainter, QPen, QBrush, QPalette,
    QLabel, QPixmap, QStackedWidget, QListWidget, QPushButton,
    QDialog, QLineEdit, QGridLayout, QDialogButtonBox, QCheckBox,
    QMessageBox, QProgressBar, QScrollArea, QSizePolicy, QFrame
)

from .utils import resource_path
from .bbclient import BBClient, SUPPORTED_VERSIONS




class MainWindow(QWidget):

    stravaCredentials = pyqtSignal(str, str)
    clearedStravaCredentials = pyqtSignal()
    abortUpload = pyqtSignal()


    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self._createWidgets()
        self._createLayout()

        self._showLoading('Searching for device')

        self._createWorkerThread()

        QTimer.singleShot(1000, self._bb_client.onStart)


    def _onUnsupportedVersion(self, ver):
        self.warning_label.setText(
        'You are using an unsupported version of BrytonBridge. '
        'It may or may not work as expected. '
        'Supported versions are (%s)' % (', '.join(SUPPORTED_VERSIONS),)
        )
        self.warning_label.show()

    def _onUploadStarted(self, tracks):

        self.upload_progress.setTracks(tracks)

        self._showWidget(self.upload_progress)


    def _onUploadStatus(self, msg):
        self._showLoading(msg)


    def _abortUpload(self):
        self.abortUpload.emit()
        self._showWidget(self.tracklist)


    def _onNeedLogin(self):

        login = LoginDialog(self)

        if login.exec_() == QDialog.Accepted:
            u = login.username.text()
            p = login.password.text()

            if login.remember.checkState() == Qt.Checked:
                self._saveStravaCredentials(u, p)

            self.stravaCredentials.emit(u, p)
        else:
            self._abortUpload()



    def _onTracksReady(self, tracks):

        self.tracklist.setTracks(tracks)
        self._showWidget(self.tracklist)


    def _onError(self, msg):
        self._showMessage('Error: %s' % msg,
                         resource_path('images/cry.png'))

    def _onDeviceOffline(self):

        self._showMessage('Please connect your device',
                         resource_path('images/connect.png'))


    def _showMessage(self, msg, icon):

        self.messages.setMessage(msg)
        self.messages.setIcon(icon)
        self._showWidget(self.messages)

    def _showLoading(self, msg):

        self.loading.setMessage(msg)
        self._showWidget(self.loading)

    def _showWidget(self, widget):

        self.widgets.setCurrentWidget(widget)


    def _onClearPassword(self):

        settings = self._getSettings()
        settings.remove('strava/username')
        settings.remove('strava/password')

        self.clearedStravaCredentials.emit()

        self.tracklist.clear_password.hide()



    def _getStravaCredentials(self):

        settings = self._getSettings()

        u = settings.value('strava/username').toString()
        p = settings.value('strava/password').toString()

        if not u or not p:
            return None, None

        return u, p


    def _saveStravaCredentials(self, username, password):

        settings = self._getSettings()

        settings.setValue('strava/username', username)
        settings.setValue('strava/password', password)

        self.tracklist.clear_password.show()



    def _getSettings(self):
        return QSettings('BrytonGPS', 'BrytonStravaUploader')

    def _createWorkerThread(self):

        self._worker_thread = QThread(self)


        u, p = self._getStravaCredentials()

        self._bb_client = BBClient(strava_username=u, strava_password=p)
        self._bb_client.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._bb_client._onThreadStart)
        self._worker_thread.finished.connect(self._bb_client.deleteLater)


        self._bb_client.tracksReady.connect(self._onTracksReady)
        self._bb_client.error.connect(self._onError)
        self._bb_client.deviceOffline.connect(self._onDeviceOffline)


        self._bb_client.stravaCredentialsNeeded.connect(self._onNeedLogin)
        self._bb_client.unsupportedBBVersion.connect(self._onUnsupportedVersion)

        self._bb_client.uploadStatus.connect(self._onUploadStatus)
        self._bb_client.stravaUploadStarted.connect(self._onUploadStarted)
        self._bb_client.stravaUploadProgress.connect(
            self.upload_progress.updateProgress)
        self._bb_client.stravaUploadFinished.connect(
            self.upload_progress.onFinished)

        self.abortUpload.connect(self._bb_client.onAbortUpload)
        self.stravaCredentials.connect(self._bb_client.onStravaCredentials)
        self.clearedStravaCredentials.connect(
            self._bb_client.onClearStravaCredentials)

        self.tracklist.requestUpload.connect(self._bb_client.onUploadTracks)


        self._worker_thread.start()


    def _createWidgets(self):


        self.widgets = QStackedWidget(self)

        self.warning_label = QLabel(self)
        self.warning_label.setStyleSheet(
            "QLabel { background-color : #FF8383;}")

        self.warning_label.setWordWrap(True)
        self.warning_label.setContentsMargins(5, 5, 5, 5)
        self.warning_label.hide()

        self.loading = LoadingWidget(self)
        self.messages = IconWidget(self)
        self.tracklist = TracklistWidget(self)
        self.upload_progress = UploadProgressWidget(self)


        self.widgets.addWidget(self.loading)
        self.widgets.addWidget(self.messages)
        self.widgets.addWidget(self.tracklist)
        self.widgets.addWidget(self.upload_progress)


        settings = self._getSettings()

        if settings.contains('strava/username') or \
           settings.contains('strava/password'):
            self.tracklist.clear_password.show()

        self.tracklist.clear_password.clicked.connect(self._onClearPassword)

        self.upload_progress.close_button.clicked.connect(self._showTracklist)


    def _showTracklist(self):
        self._showWidget(self.tracklist)


    def _createLayout(self):

        l = QVBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)

        l.addWidget(self.warning_label)

        logo = QLabel(self)

        pix = QPixmap(resource_path('images/logo.png'))
        pix = pix.scaledToWidth(400, Qt.SmoothTransformation)
        logo.setPixmap(pix)
        l.addWidget(logo)

        l.addWidget(self.widgets, 1)

        self.setLayout(l)




class IconWidget(QWidget):

    def __init__(self, parent=None):
        super(IconWidget, self).__init__(parent)

        self.message = QLabel(self)

        self.message.setAlignment(Qt.AlignCenter)

        self.icon = QLabel(self)
        self.icon.setAlignment(Qt.AlignCenter)

        self._createLayout()


    def setIcon(self, path):
        pix = QPixmap(path)
        pix = pix.scaledToHeight(200, Qt.SmoothTransformation)
        self.icon.setPixmap(pix)


    def setMessage(self, msg):
        self.message.setText('<b>%s</b>' % msg)


    def _createLayout(self):

        l = QVBoxLayout()
        l.addStretch(1)
        l.addWidget(self.message)
        l.addSpacing(10)
        l.addWidget(self.icon)
        l.addStretch(1)

        self.setLayout(l)



class LoadingWidget(QWidget):

    def __init__(self, parent=None):
        super(LoadingWidget, self).__init__(parent)


        self.message = QLabel(self)
        self.message.setAlignment(Qt.AlignCenter)

        self._createLayout()

    def setMessage(self, msg):
        self.message.setText('<b>%s</b>' % msg)

    def _createLayout(self):

        l = QVBoxLayout()

        l.addStretch(1)
        l.addWidget(self.message)

        l.addSpacing(10)
        spinner = BusySpinnerWidget(self)

        l.addWidget(spinner)
        l.addStretch(1)

        self.setLayout(l)





class TracklistWidget(QWidget):

    requestUpload = pyqtSignal(list)


    def __init__(self, parent=None):
        super(TracklistWidget, self).__init__(parent)

        self.tracklist = QListWidget(self)
        self.tracklist.setSelectionMode(QListWidget.NoSelection)

        self.upload_button = QPushButton(
            QIcon(resource_path('images/strava-button.png')),
                  'Upload to Strava', self)
        self.upload_button.setMinimumHeight(50)
        self.upload_button.setIconSize(QSize(40, 40))

        self.clear_password = QPushButton(
            QIcon(resource_path('images/cross.png')),
                  'Clear password', self)
        self.clear_password.setMinimumHeight(50)
        self.clear_password.setIconSize(QSize(20, 20))
        self.clear_password.hide()


        self.upload_button.clicked.connect(self._onUploadClicked)

        self._createLayout()



    def setTracks(self, tracks):
        self.tracklist.clear()
        self.tracklist.addItems(tracks)

        for i, name in enumerate(tracks):
            self.tracklist.item(i).setCheckState(Qt.Unchecked)
            self.tracklist.item(i).setSizeHint(QSize(200, 25))

        if tracks:
            self.tracklist.item(i).setCheckState(Qt.Checked)
            self.upload_button.setEnabled(True)
        else:
            self.upload_button.setEnabled(False)


    def _onUploadClicked(self):

        ids = []
        for i in range(self.tracklist.count()):

            item = self.tracklist.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(i)


        if ids:
            self.requestUpload.emit(ids)



    def _createLayout(self):

        l = QVBoxLayout()
        l.addWidget(self.tracklist)

        h = QHBoxLayout()
        h.addWidget(self.upload_button)
        h.addWidget(self.clear_password)
        l.addLayout(h)

        self.setLayout(l)



class LoginDialog(QDialog):

    def __init__(self, parent=None):
        super(LoginDialog, self).__init__(parent)


        self.username = QLineEdit(self)
        self.username.setPlaceholderText('Strava email')
        self.username_label = QLabel('Email', self)
        self.username_label.setBuddy(self.username)
        self.username_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.password = QLineEdit(self)
        self.password.setPlaceholderText('Strava password')
        self.password.setEchoMode(QLineEdit.Password)
        self.password_label = QLabel('Password', self)
        self.password_label.setBuddy(self.password)
        self.password_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)


        self.buttons = QDialogButtonBox(self)
        self.buttons.addButton(QDialogButtonBox.Ok)
        self.buttons.addButton(QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText('Login')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancel')

        self.buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.buttons.button(QDialogButtonBox.Cancel). \
                clicked.connect(self.reject)


        self.remember = QCheckBox('Remember login', self)

        self.remember.stateChanged.connect(self._onClickRemember)

        self.setWindowTitle('Strava login')

        self.resize(300, 140)

        self._createLayout()


    def _onClickRemember(self, state):

        if state == Qt.Checked:
            QMessageBox.warning(self, 'Warning', 'Password will be stored '
                                'as plain text')



    def _createLayout(self):

        l = QGridLayout(self)

        l.addWidget(self.username_label, 0, 0)
        l.addWidget(self.username, 0, 1)

        l.addWidget(self.password_label, 1, 0)
        l.addWidget(self.password, 1, 1)

        l.addWidget(self.remember, 2, 1, Qt.AlignRight)

        l.addWidget(self.buttons, 3, 0, 1, 2)

        self.setLayout(l)



class UploadProgressWidget(QWidget):

    def __init__(self, parent=None):
        super(UploadProgressWidget, self).__init__(parent)


        self.close_button = QPushButton('Back', self)
        self.close_button.setMinimumHeight(50)

        self._first_display = True


    def updateProgress(self, tracks):

        for track in tracks:
            w = self._widgets[track['id']]

            if 'error' in track and track['error']:
                w.label.setText('<font color="red">%s</font>' % track['error'])
                w.progress.setValue(100)

            elif track['name'] is not None:
                w.label.setText(track['name'])
                w.progress.setValue(track['progress'])

                if track['progress'] == 100:

                    if 'activity' in track and 'activity_url' in track['activity']:
                        name = track['activity']['name']
                        url = track['activity']['activity_url']
                        w.label.setText(
                            '<a href="%s"><font color="green">%s</font></a>' \
                            % (url, name))
                    else:
                        name = track['name']
                        w.label.setText('<font color="green">%s</font>' % name)


    def onFinished(self, tracks):
        self.updateProgress(tracks)
        self.close_button.setEnabled(True)


    def setTracks(self, tracks):

        if not self._first_display:
            self._removeOldWidgets()

        self._first_display = False

        self._widgets = {}
        parent = QWidget(self)
        l = QVBoxLayout(parent)
        for track in tracks:
            w = self._createTrackProgress(parent, track)
            l.addWidget(w)
            self._widgets[track['id']] = w

        l.addStretch(1)
        parent.setLayout(l)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(parent)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setFrameShape(QFrame.NoFrame);

        l = QVBoxLayout(self)
        l.addWidget(scroll)
        l.addWidget(self.close_button)
        self.setLayout(l)

        self.close_button.setEnabled(False)


    def _removeOldWidgets(self):


        self.layout().removeWidget(self.close_button)

        self._widgets = {}

        QWidget().setLayout(self.layout())





    def _createTrackProgress(self, parent, track):

        w = QWidget(parent)
        l = QVBoxLayout(w)


        p = QProgressBar(w)
        p.setRange(0, 100)
        p.setValue(track['progress'])
        w.progress = p

        label = QLabel(w)
        label.setContentsMargins(5, 2, 5, 2)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        if track['name'] is not None:
            label.setText(track['name'])
        elif track['error']:
            label.setText('<font color="red">%s</font>' % track['error'])
            p.setValue(100)

        w.label = label


        l.addWidget(label)
        l.addWidget(p)

        w.setLayout(l)

        return w







class BusySpinnerWidget(QWidget):

    def __init__(self, parent=None):
        super(BusySpinnerWidget, self).__init__(parent)

        self.setMinimumSize(200, 200)


    def paintEvent(self, event):

        painter = QPainter()
        painter.begin(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self.palette().color(QPalette.Highlight)))


        num = 8

        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(360.0/num * (self.counter % num))

        for i in range(num):
            s = 25 + i

            x =  50 * math.cos(2.0 * math.pi * i / num) - s/2.0
            y =  50 * math.sin(2.0 * math.pi * i / num) - s/2.0


            painter.drawEllipse(
                x,
                y,
                s, s)
        painter.end()




    def showEvent(self, event):
        self.timer = self.startTimer(100)
        self.counter = 0

    def hideEvent(self, event):
        self.killTimer(self.timer)


    def timerEvent(self, event):

        self.counter += 1
        self.update()



def main():

    app = QApplication(sys.argv)

    win = MainWindow()

    win.setFixedSize(400, 600)
    win.setWindowTitle('Bryton Strava Uploader')
    win.setWindowIcon(QIcon(resource_path('images/bryton.png')))
    win.show()

    return app.exec_()





if __name__ == '__main__':
    main()


