import typing
from PyQt5.QtCore import QProcess, QObject, pyqtSignal, QTimer, pyqtSlot


class Status(QObject):
    qprocess: QProcess = ...
    timer: QTimer = ...

    class SessionState:
        STOPPED = 0
        RUNNING = 1

    class ContainerState:
        FROZEN = 0
        NOT_FROZEN = 1

    sessionStatusChanged = pyqtSignal(int)
    containerStatusChanged = pyqtSignal(int)

    def __init__(self, parent: typing.Optional['QObject'] = None) -> None:
        super().__init__(parent)
        self.session_state = self.SessionState.STOPPED
        self.container_state = self.ContainerState.NOT_FROZEN

        self.qprocess = QProcess()
        self.timer = QTimer()
        self.timer.start(5000)

        self.timer.timeout.connect(self.get_state)
        self.qprocess.readyReadStandardOutput.connect(self.update_status)

        # self.sessionStatusChanged.connect()

    @pyqtSlot()
    def update_status(self):
        output = str(self.qprocess.readAllStandardOutput(), encoding="utf-8")
        outpput_list = output.split("\n")
        session_state = self.session_state
        container_state = self.container_state
        for line in outpput_list:
            if "Session" in line:
                if "STOPPED" in line:
                    session_state = self.SessionState.STOPPED
                elif "RUNNING" in line:
                    session_state = self.SessionState.RUNNING
            if "Container" in line:
                if "FROZEN" in line:
                    container_state = self.ContainerState.FROZEN
                else:
                    container_state = self.ContainerState.NOT_FROZEN
        if session_state != self.session_state:
            self.session_state = session_state
            self.sessionStatusChanged.emit(self.session_state)

        if container_state != self.container_state:
            self.container_state = container_state
            self.containerStatusChanged.emit(self.container_state)

    @pyqtSlot()
    def get_state(self):
        args = ["status"]
        self.qprocess.start("waydroid", args)

