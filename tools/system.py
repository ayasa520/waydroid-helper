import typing
from PyQt5.QtCore import QProcess, QObject, pyqtSlot, QByteArray
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusPendingCallWatcher, QDBusPendingReply

# from tools.status import Status


class System(QObject):
    m_process_list = list()
    bus = QDBusConnection.systemBus()
    interface = QDBusInterface("com.waydroid.Helper", "/Waydroid",
                               "com.waydroid.HelperInterface",
                               bus)

    def __init__(self, parent: typing.Optional['QObject'] = ...) -> None:
        super().__init__(parent)
        self.qprocess = QProcess()
        self.unfreeze_container()



    def session_start(self):
        args = ["session", "start"]
        process = QProcess()
        process.setProperty("method", "session_start")
        self.m_process_list.append(process)
        # process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_process_finished)
        process.start("waydroid", args)
        process.startDetached("start")

    def session_stop(self):
        args = ["session", "stop"]
        process = QProcess()
        process.setProperty("method", "session_stop")
        self.m_process_list.append(process)
        # process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_process_finished)
        process.start("waydroid", args)
        process.start("start")

    def show_full_ui(self):
        args = ["show-full-ui"]
        process = QProcess()
        process.setProperty("method", "show_full_ui")
        self.m_process_list.append(process)
        # process.readyReadStandardOutput.connect(self.readOutput)
        process.finished.connect(self.on_process_finished)
        process.start("waydroid", args)
        process.startDetached("start")

    @pyqtSlot()
    def unfreeze_container(self):
        call = self.interface.asyncCall("Unfreeze")
        watcher = QDBusPendingCallWatcher(call, self.interface)
        # connect the finished signal to a slot
        watcher.finished.connect(self.call_finished)

    def logcat(self):
        self.bus.connect( "com.waydroid.Helper",  # service name
                         "/Waydroid",  # object path
                         "com.waydroid.HelperInterface",  # interface name
                         "logcat_signal",  # signal name
                         self.on_logcat)  # slot function
        call=self.interface.asyncCall("Logcat")
        watcher = QDBusPendingCallWatcher(call,self.interface)
        # connect the finished signal to a slot
        watcher.finished.connect(self.call_finished)

    @pyqtSlot(QByteArray)
    def on_logcat(self, output):
        print(output)

    @pyqtSlot(QDBusPendingCallWatcher)
    def call_finished(self, watcher: QDBusPendingCallWatcher):
        # get the reply from the watcher
        reply = QDBusPendingReply(watcher)

        # check for errors
        if reply.isError():
            # handle error
            print("Error:", reply.error().message())
        else:
            # get the return value
            # value = reply.argumentAt(0)
            pass
            # do something with value
            # print("Value:", value)

        # delete the watcher
        watcher.deleteLater()

    @pyqtSlot()
    def readOutput(self):
        process: QProcess = self.sender()
        if not process:
            return
        output = process.readAllStandardOutput()
        method = process.property("method")
        if method == "session_stop":
            print("session_stop")

        # print("output", str(output,encoding="utf-8"))
    @pyqtSlot()
    def on_process_finished(self):
        process: QProcess = self.sender()
        self.m_process_list.remove(process)
        process.deleteLater()

    def close_logcat(self):
        print("close logcat")
        self.interface.call("StopLogcat")
        self.bus.disconnect( "com.waydroid.Helper",  # service name
                         "/Waydroid",  # object path
                         "com.waydroid.HelperInterface",  # interface name
                         "logcat_signal",  # signal name
                         self.on_logcat)



# app = QApplication([])
# a = System(app)
# a.logcat()

# t=QTimer()
# t.start(10000)
# def on_time():
#     print("timeout")
#     a.close_logcat()
# t.timeout.connect(on_time)
# a.unfreeze_container()

# app.exec_()
