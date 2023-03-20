import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt5 import QtCore
from PyQt5.QtCore import qDebug, QSharedMemory, QSystemSemaphore
from model.basepropmodel import BasePropModel
from model.generalcfgmodel import GeneralCfgModel
from tools.app import App
from tools.qmlsocket import TcpSocket
from tools.status import Status

if __name__ == '__main__':

    app = QApplication([])

    if os.getuid() == 0:
        qDebug("Don't start as a super user!")
        QMessageBox.warning(
            None, "Warning", "Don't start as a super user!"
        )
        app.quit()
        sys.exit(0)

    semaphore = QSystemSemaphore("myAppSemaphore", 1)
    semaphore.acquire()
    sharedMemory1 = QSharedMemory("waydroid_helper")
    isRunning = False
    if (sharedMemory1.attach()):
        isRunning = True
    else:
        sharedMemory1.create(1)
        isRunning = False
    semaphore.release()

    if (isRunning):
        qDebug("Application is alreadly running!")
        QMessageBox.information(
            None, "Warning", "Application is alreadly running!"
        )
        app.quit()
        sys.exit(0)

    engine = QQmlApplicationEngine()
    qmlRegisterType(TcpSocket, "Tcp", 1, 0, "Tcp")
    engine.rootContext().setContextProperty("BasePropModel", BasePropModel(engine))
    engine.rootContext().setContextProperty("GeneralCfgModel", GeneralCfgModel(engine))
    engine.rootContext().setContextProperty("App", App(engine))
    engine.rootContext().setContextProperty("Status", Status(engine))
    engine.load(QtCore.QUrl.fromLocalFile("qml/main.qml"))
    window = engine.rootObjects()[0]
    window.show()
    sys.exit(app.exec_())
