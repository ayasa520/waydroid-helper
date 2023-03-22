from PyQt5.QtCore import Qt, QAbstractItemModel, QObject, QModelIndex, QVariant, pyqtSlot, QByteArray,QTimer
from tools.prop import Prop
import typing


class GeneralCfgModel(QAbstractItemModel):
    def __init__(self, parent: typing.Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.prop = Prop(self)
        # Because it's slow to get prop from waydroid prop, so don't wait for all the prop to be loaded
        self.enabled = False
        self.data_list = [
            {
                "key": "persist.waydroid.fake_wifi",
                "description": "Comma separated list of package names for which the system will always appear as if connected to wifi",
                "value": "",
                "old_val": "",
                "type": "string"
            },
            {
                "key": "persist.waydroid.multi_windows",
                "description": "Enables/Disables window integration with the desktop",
                "value": "false",
                "old_val": "false",
                "type": "bool"
            }, {
                "key": "persist.waydroid.fake_touch",
                "description": "Comma separated list of package names for which mouse inputs should be interpreted as touch inputs instead",
                "value": "",
                "old_val": "",
                "type": "string"
            }, {
                "key": "persist.waydroid.cursor_on_subsurface",
                "description": "Workaround for showing the cursor in multi_windows mode on some compositors",
                "value": "false",
                "old_val": "false",
                "type": "bool"
            }, {
                "key": "persist.waydroid.invert_colors",
                "description": "Swaps the color space from RGBA to BGRA (only works with our patched mutter so far)",
                "value": "false",
                "old_val": "false",
                "type": "bool"
            }, {
                "key": "persist.waydroid.height_padding",
                "description": "0-9999(int) Adjust height padding",
                "value": "",
                "old_val": "",
                "type": "int"
            }, {
                "key": "persist.waydroid.width_padding",
                "description": "0-9999 (int) Adjust width padding",
                "value": "",
                "old_val": "",
                "type": "int"
            }, {

                "key": "persist.waydroid.width",
                "description": "0-9999 (int) Used for user to override desired resolution",
                "value": "",
                "old_val": "",
                "type": "int"

            }, {
                "key": "persist.waydroid.height",
                "description": "0-9999 (int) Used for user to override desired resolution",
                "value": "",
                "old_val": "",
                "type": "int"
            }, {

                "key": "persist.waydroid.suspend",
                "description": "Let the Waydroid container sleep when no apps are active",
                "value": "false",
                "old_val": "false",
                "type": "bool"
            }
        ]
        self.initData()
        self.prop.GetProp.connect(self.loadData)
        self.prop.FailedSetProp.connect(self.on_failed_set)

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
            return self.enabled
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        # 修改模型中的数据，并发出dataChanged信号
        if role == Qt.ItemDataRole.EditRole:
            if self.data_list[index.row()]["value"] != value:
                self.data_list[index.row(
                )]["old_val"] = self.data_list[index.row()]["value"]
                self.data_list[index.row()]["value"] = value
                self.saveData(index, index)
                self.dataChanged.emit(index, index)
                return True
        return False

    @pyqtSlot(str, str)
    def loadData(self, key, value):
        for i in range(len(self.data_list)):
            if key == self.data_list[i]["key"]:
                self.data_list[i]["old_val"] = self.data_list[i]["value"]
                if self.data_list[i]["type"] == "bool" and value=="":
                    value = "false"
                self.data_list[i]["value"] = value
                self.dataChanged.emit(self.index(i, 0),
                                      self.index(i, 0))
                break

    def initData(self):
        for i in range(len(self.data_list)):
            self.prop.get_prop(self.data_list[i]["key"])

    @pyqtSlot(QModelIndex, QModelIndex)
    def saveData(self, index1: QModelIndex, index2: QModelIndex):
        for row in range(index1.row(), index2.row()+1):
            key = self.data_list[row]["key"]
            value = self.data_list[row]["value"]
            self.prop.set_prop(key, value)

    @pyqtSlot(str, str)
    def on_failed_set(self, key, value):
        for i in range(len(self.data_list)):
            if key == self.data_list[i]["key"] and self.data_list[i]["old_val"] != self.data_list[i]["value"]:
                self.data_list[i]["value"] = self.data_list[i]["old_val"]
                self.dataChanged.emit(self.index(i, 0),
                                      self.index(i, 0))
                break

    def roleNames(self) -> typing.Dict[int, 'QByteArray']:
        roles = super().roleNames()
        roles[Qt.ItemDataRole.UserRole+1] = QByteArray(b"isEnabled")
        return roles

    @pyqtSlot()
    def disable(self):
        self.enabled = False
        for i in range(len(self.data_list)):
            self.dataChanged.emit(self.index(i, 0), self.index(i, 0))

    @pyqtSlot()
    def enable(self):
        self.enabled = True
        self.initData()