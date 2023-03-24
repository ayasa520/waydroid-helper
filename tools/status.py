import typing
from PyQt5.QtCore import QProcess, QObject, pyqtSignal, QTimer, pyqtSlot
from tools.prop import Prop


class Status(QObject):
    qprocess: QProcess = ...
    timer: QTimer = ...

    class SessionState:
        STOPPED = 0
        STARTING = 1
        RUNNING = 2

    class ContainerState:
        FROZEN = 0
        NOT_FROZEN = 1

    sessionStatusChanged = pyqtSignal(int)
    containerStatusChanged = pyqtSignal(int)
    prop = Prop()

    def __init__(self, parent: typing.Optional['QObject'] = None) -> None:
        super().__init__(parent)
        self.session_state = self.SessionState.STOPPED
        self.container_state = self.ContainerState.NOT_FROZEN
        self.bootComplete = False

        self.qprocess = QProcess()
        self.timer = QTimer()
        self.timer.start(5000)

        self.timer.timeout.connect(self.get_state)
        self.qprocess.readyReadStandardOutput.connect(self.update_status)
        self.prop.GetProp.connect(self.onGetProp)

        # self.sessionStatusChanged.connect()
    
    @pyqtSlot(str, str)
    def onGetProp(self, key, value):
        if key=="sys.boot_completed":
            if value=="1":
                if self.bootComplete==False:
                    self.bootComplete=True
                    self.get_state()
            else:
                self.bootComplete=False


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
                    if self.bootComplete:
                        session_state = self.SessionState.RUNNING
                    else:
                        session_state = self.SessionState.STARTING
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
        self.qprocess.waitForFinished()
        self.qprocess.start("waydroid", args)
        self.prop.get_prop("sys.boot_completed")

