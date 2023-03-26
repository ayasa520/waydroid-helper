from PyQt5.QtCore import Qt, QAbstractItemModel, QObject, QModelIndex, QVariant, pyqtSlot, QByteArray
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusPendingCallWatcher, QDBusPendingReply
import typing


class BasePropModel(QAbstractItemModel):
    def __init__(self, parent: typing.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.enabled = False
        self.data_list = {
            "sys.use_memfd": {
                "description": "replace ashmem with memfd",
                "value": "",
                "old_val": "",
                "type": "bool"
            }, "qemu.hw.mainkeys": {
                "description": "Set to 1 to hide navbar",
                "value": "",
                "old_val": "",
                "type": "bool"
            }
        }
        self.base_prop_path = "/var/lib/waydroid/waydroid_base.prop"
        self.loadData()

        self.bus = QDBusConnection.systemBus()
        self.interface = QDBusInterface("com.waydroid.Helper", "/Waydroid",
                                        "com.waydroid.HelperInterface",
                                        self.bus)

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        return self.createIndex(row, column)

    def parent(self, child: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.data_list)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        # return len(self.data_list[0])
        return 1

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        key = list(self.data_list.keys())[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return key
        elif role == Qt.ItemDataRole.EditRole:
            return self.data_list[key]["value"]
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self.data_list[key]["description"]
        elif role == Qt.ItemDataRole.UserRole:
            return self.data_list[key]
        elif role == Qt.ItemDataRole.UserRole+1:
            return self.enabled
        elif role == Qt.ItemDataRole.UserRole+2:
            return self.data_list[key]["type"]
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        # 修改模型中的数据，并发出dataChanged信号
        if role == Qt.ItemDataRole.EditRole:
            key = list(self.data_list.keys())[index.row()]
            if self.data_list[key]["value"] != value:
                self.data_list[key]["old_val"] = self.data_list[key]["value"]
                self.data_list[key]["value"] = value
                self.saveData(index, index)
                self.dataChanged.emit(index, index)
                return True
        return False

    def loadData(self):
        with open(self.base_prop_path, "r") as f:
            content = f.readlines()

            def foo(x: str):
                items = x.split("=")
                key = items[0].strip()
                value = items[1].strip()
                if key not in self.data_list.keys():
                    self.data_list[key] = {
                        "value": "", "description": "", "old_val": "", "type": ""}
                self.data_list[key]["value"] = value
                if value == "True" or value == "true" or value == "False" or value == "false":
                    self.data_list[key]["type"] = "bool"
                else:
                    self.data_list[key]["type"] = "string"
                return
            for i in content:
                foo(i)
        self.enable()

    @pyqtSlot(QModelIndex, QModelIndex)
    def saveData(self, index1: QModelIndex, index2: QModelIndex):
        for row in range(index1.row(), index2.row()+1):
            key = list(self.data_list.keys())[row]
            call = self.interface.asyncCall(
                "SetBaseProp", key, self.data_list[key]["value"])
            watcher = QDBusPendingCallWatcher(call, self.interface)
            watcher.finished.connect(lambda: self.call_finished(watcher, row))

    @pyqtSlot(QDBusPendingCallWatcher, int)
    def call_finished(self, watcher: QDBusPendingCallWatcher, row: int):
        # get the reply from the watcher
        reply = QDBusPendingReply(watcher)

        # check for errors
        if reply.isError():
            # handle error
            print("Error:", reply.error().message())
            key = list(self.data_list.keys())[row]
            self.data_list[key]["value"] = self.data_list[key]["old_val"]
            self.dataChanged.emit(self.index(row, 0), self.index(row, 0))
        else:
            # get the return value
            value = reply.argumentAt(0)
            # do something with value
            print("Value:", value)

        # delete the watcher
        watcher.deleteLater()

    def roleNames(self) -> typing.Dict[int, 'QByteArray']:
        roles = super().roleNames()
        roles[Qt.ItemDataRole.UserRole+1] = QByteArray(b"isEnabled")
        roles[Qt.ItemDataRole.UserRole+2] = QByteArray(b"type")
        return roles

    @pyqtSlot()
    def disable(self):
        pass

    @pyqtSlot()
    def enable(self):
        self.enabled = True
        print(self.enabled)
        for i in range(len(self.data_list)):
            self.dataChanged.emit(self.index(i,0),self.index(i, 0))
