import typing
import os
import shutil
from PyQt5.QtCore import QProcess, QObject, pyqtSlot, qDebug, pyqtSignal
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusPendingCallWatcher, QDBusPendingReply

# need session and container both running


class App(QObject):
    # qprocess: QProcess = ...
    m_process_list = list()
    tmp_dir = os.path.expanduser(
        "~")+"/.local/share/waydroid/data/waydroid_tmp"
    bus = QDBusConnection.systemBus()
    interface = QDBusInterface("com.waydroid.Helper", "/Waydroid",
                               "com.waydroid.HelperInterface",
                               bus)
    installSuccess = pyqtSignal(str)

    def __init__(self, parent: typing.Optional['QObject'] = ...) -> None:
        super().__init__(parent)

    @pyqtSlot(str)
    def install(self, app):

        @pyqtSlot(QDBusPendingCallWatcher)
        def call_finished(watcher: QDBusPendingCallWatcher):
            reply = QDBusPendingReply(watcher)
            if reply.isError():
                qDebug("Error: " + reply.error().message())
            else:
                value = reply.argumentAt(0)
                if value.strip()=="Success":
                    self.installSuccess.emit(app)
            watcher.deleteLater()

        if not os.path.isdir(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        shutil.copy(app, self.tmp_dir)
        call = self.interface.asyncCall("InstallApk", app.split("/")[-1])
        watcher = QDBusPendingCallWatcher(call, self.interface)
        watcher.finished.connect(call_finished)

    @pyqtSlot(str)
    def uninstall(self, package):
        args = ["app", "uninstall", package]
        process = QProcess()
        process.setProperty("method", "uninstall")
        self.m_process_list.append(process)
        process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_finished)
        process.start("waydroid", args)

    @pyqtSlot(str)
    def launch(self, package):

        args = ["app", "lauch", package]
        process = QProcess()
        process.setProperty("method", "lauch")
        self.m_process_list.append(process)
        process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_finished)
        process.start("waydroid", args)

    @pyqtSlot(str)
    def list(self):
        args = ["app", "list"]
        process = QProcess()
        process.setProperty("method", "list")
        self.m_process_list.append(process)
        process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_finished)
        process.start("waydroid", args)

    @pyqtSlot()
    def readOutput(self):
        process: QProcess = self.sender()
        if not process:
            return
        output = process.readAllStandardOutput()
        method = process.property("method")
        if method == "uninstall":
            print("uninstall")
        elif method == "launch":
            print("launch")
        elif method == "list":
            print("list")
        # print("output", str(output,encoding="utf-8"))

    @pyqtSlot()
    def on_finished(self):
        process: QProcess = self.sender()
        self.m_process_list.remove(process)
        process.deleteLater()
