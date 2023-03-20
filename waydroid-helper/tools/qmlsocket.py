import time
import dbus
import os
from PyQt5.QtNetwork import QTcpSocket, QHostAddress
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusPendingCallWatcher, QDBusPendingReply
from PyQt5 import QtCore


class TcpSocket(QTcpSocket):

    bus = QDBusConnection.systemBus()
    interface = QDBusInterface("com.waydroid.Helper", "/Waydroid",
                               "com.waydroid.HelperInterface",
                               bus)
    readyReadLine = QtCore.pyqtSignal(bytes)
    test = QtCore.pyqtSignal(bytes, int)
    secret = ...
    port = ...
    host = ...

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected.connect(self.on_connected)
        self.error.connect(self.atError)
        self.port = 25000
        self.host = "127.0.0.1"

    @QtCore.pyqtSlot()
    def on_connected(self):
        self.write(self.secret.encode("utf-8"))
        self.waitForReadyRead(1000)

    @QtCore.pyqtSlot()
    def atError(self):
        print(self.errorString())

    @QtCore.pyqtSlot()
    def closeEvent(self):
        self.close()
        call = self.interface.asyncCall("StopShell")
        watcher = QDBusPendingCallWatcher(call, self.interface)

        def error(w):
            reply = QDBusPendingReply(w)
            if reply.isError():
                print("Error:", reply.error().message())
            w.deleteLater()
        watcher.finished.connect(error)

    @QtCore.pyqtSlot(int)
    def os_write(self, fd):
        self.timer = QtCore.QTimer()
        self.timer.start(1)
        def onTimeout():
            data = bytes(self.read(2048))
            if not data:
                self.timer.stop()
                self.timer.deleteLater()
            else:
                os.write(fd, data)
        self.timer.timeout.connect(onTimeout)

    @QtCore.pyqtSlot()
    def init(self):
        call = self.interface.asyncCall("StartShell")

        def on_finished(w):
            reply = QDBusPendingReply(w)
            if reply.isError():
                print("Error:", reply.error().message())
            else:
                self.secret = reply.argumentAt(0)
                self.connectToHost(QHostAddress(self.host), self.port)
            w.deleteLater()

        watcher = QDBusPendingCallWatcher(call, self.interface)
        watcher.finished.connect(on_finished)

    @QtCore.pyqtSlot()
    def reconnect_if_need(self):
        if self.state() == 0:
            self.init()

    @QtCore.pyqtSlot(str)
    def on_write(self, data: str):
        self.write(data.encode("utf-8"))
