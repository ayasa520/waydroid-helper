from PyQt5.QtCore import Qt, QAbstractItemModel, QObject, QModelIndex, QVariant, pyqtSlot, QByteArray
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusPendingCallWatcher, QDBusPendingReply
import typing


descriptions = {
    "qemu.hw.mainkeys": "Set to 1 to hide navbar",
    "sys.use_memfd": "replace ashmem with memfd"
}


class BasePropModel(QAbstractItemModel):
    def __init__(self, parent: typing.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.data_list = []
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
        if role == Qt.ItemDataRole.DisplayRole:
            return self.data_list[index.row()]["key"]
        elif role == Qt.ItemDataRole.EditRole:
            return self.data_list[index.row()]["value"]
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self.data_list[index.row()]["description"]
        elif role == Qt.ItemDataRole.UserRole:
            return self.data_list[index.row()]
        elif role == Qt.ItemDataRole.UserRole+1:
            return self.data_list[index.row()]["enabled"]
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        # 修改模型中的数据，并发出dataChanged信号
        if role == Qt.ItemDataRole.EditRole:
            if self.data_list[index.row()]["value"] != value:
                self.data_list[index.row()]["value"] = value
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
                description = descriptions[key] if key in descriptions.keys(
                ) else ""

                return {"key": key, "description": description, "value": value, "enabled": True}
            result = map(foo, content)
            self.data_list = list(result)
            for item in self.data_list:
                if item["key"] == "qemu.hw.mainkeys":
                    return
            self.data_list.append(
                {"key": "qemu.hw.mainkeys", "description": "hide navbar. Set to 1 to hide",
                    "value": "0", "enabled": True}
            )

    @pyqtSlot(QModelIndex, QModelIndex)
    def saveData(self, index1: QModelIndex, index2: QModelIndex):
        for row in range(index1.row(), index2.row()+1):
            call = self.interface.asyncCall(
                "SetBaseProp", self.data_list[row]["key"], self.data_list[row]["value"])
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
            self.loadData()
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
        return roles

    @pyqtSlot(int)
    def refreshEnabledByStatus(self, flag):
        pass

    @pyqtSlot(int)
    def refreshEnabledByDbus(self, flag):
        pass