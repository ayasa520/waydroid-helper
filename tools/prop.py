import typing
from PyQt5.QtCore import QProcess, QObject, pyqtSlot, pyqtSignal


class Prop(QObject):
    m_process_list = list()
    GetProp = pyqtSignal(str, str)
    FailedGetProp = pyqtSignal(str)
    FailedSetProp = pyqtSignal(str, str)

    def __init__(self, parent: typing.Optional['QObject'] = None) -> None:
        super().__init__(parent)

    def get_prop(self, key):
        args = ["prop", "get", key]
        process = QProcess(self)
        process.setProperty("method", "get_prop")
        process.setProperty("key", key)
        self.m_process_list.append(process)
        # process.readyReadStandardOutput.connect(self.read_output)
        process.finished.connect(self.on_finished)
        process.errorOccurred.connect(self.on_error)
        process.readyReadStandardError.connect(self.on_stderr)
        process.start("waydroid", args)

    def set_prop(self, key, value):
        args = ["prop", "set", key, value]
        process = QProcess(self)
        process.setProperty("method", "set_prop")
        process.setProperty("key", key)
        process.setProperty("value", value)
        self.m_process_list.append(process)
        # process.readyReadStandardOutput.connect(self.read_output)
        process.finished.connect(self.on_finished)
        process.errorOccurred.connect(self.on_error)
        process.readyReadStandardError.connect(self.on_stderr)
        process.start("waydroid", args)

    # @pyqtSlot()
    # def read_output(self):
    #     process: QProcess = self.sender()
    #     if not process:
    #         return
    #     output = process.readAllStandardOutput()
    #     method = process.property("method")
    #     if method == "get_prop":
    #         key = process.property("key")
    #         value = str(output, encoding="utf-8").strip()
    #         self.GetProp.emit(key, value)

    @pyqtSlot()
    def on_finished(self):
        process: QProcess = self.sender()
        method = process.property("method")
        if method == "get_prop":
            output = process.readAllStandardOutput()+b''
            key = process.property("key")
            value = str(output, encoding="utf-8").strip()
            self.GetProp.emit(key, value)
        self.m_process_list.remove(process)
        process.deleteLater()
    
    @pyqtSlot()
    def on_stderr(self):
        process: QProcess = self.sender()
        print(str(process.readAllStandardError(),encoding="utf-8").strip())
        key = process.property("key")
        if process.property("method") == "get_prop":
            self.FailedGetProp.emit(key)
        elif process.property("method") == "set_prop":
            value = process.property("value")
            self.FailedSetProp.emit(key, value)


    @pyqtSlot()
    def on_error(self):
        process: QProcess = self.sender()
        print("ProcessError:", process.ProcessError())
        key = process.property("key")
        if process.property("method") == "get_prop":
            self.FailedGetProp.emit(key)
        elif process.property("method") == "set_prop":
            value = process.property("value")
            self.FailedSetProp.emit(key, value)


