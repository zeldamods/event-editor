from enum import IntEnum, auto
import typing

import eventeditor.util as util
from evfl import ActorIdentifier, Argument, Container
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ContainerModelColumn(IntEnum):
    DataType = 0
    Key = auto()
    Value = auto()

class ContainerModel(qc.QAbstractTableModel):
    def __init__(self, parent, container: typing.Optional[Container] = None) -> None:
        super().__init__(parent)
        self.set(container)

    def set(self, container: typing.Optional[Container]) -> None:
        self.beginResetModel()
        if container:
            self.cdata = container.data
            self.keys = list(container.data.keys())
        else:
            self.cdata = dict()
            self.keys = []
        self.endResetModel()

    def has(self, key: str) -> bool:
        return any(k == key for k in self.cdata.keys())

    def insertItem(self, key: str, value) -> bool:
        self.beginInsertRows(qc.QModelIndex(), len(self.keys), len(self.keys))
        self.cdata[key] = value
        self.keys.append(key)
        self.endInsertRows()
        return True

    def removeRow(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        del self.cdata[self.keys[row]]
        self.keys.pop(row)
        self.endRemoveRows()
        return True

    def changeTypeToArgument(self, row: int) -> None:
        self.cdata[self.keys[row]] = Argument()
        self.dataChanged.emit(self.createIndex(row, ContainerModelColumn.DataType), self.createIndex(row, ContainerModelColumn.Value))

    def columnCount(self, parent) -> int:
        return len(ContainerModelColumn)

    def rowCount(self, parent) -> int:
        return len(self.cdata)

    def flags(self, index: qc.QModelIndex):
        if index.column() != ContainerModelColumn.Value:
            return super().flags(index)
        row = index.row()
        if isinstance(self.cdata[self.keys[row]], bool):
            return super().flags(index) | qc.Qt.ItemIsUserCheckable
        return super().flags(index) | qc.Qt.ItemIsEditable

    def headerData(self, section, orientation, role) -> qc.QVariant:
        if role != qc.Qt.DisplayRole:
            return qc.QVariant()
        if section == ContainerModelColumn.Key:
            return 'Key'
        if section == ContainerModelColumn.Value:
            return 'Value'
        if section == ContainerModelColumn.DataType:
            return 'Type'
        return 'Unknown'

    def setData(self, index: qc.QModelIndex, value, role: qc.Qt.ItemDataRole) -> bool:
        col = index.column()
        row = index.row()
        current_value = self.cdata[self.keys[row]]

        if role == qc.Qt.CheckStateRole:
            if col != ContainerModelColumn.Value or not isinstance(current_value, bool):
                return False
            self.cdata[self.keys[row]] = True if value == qc.Qt.Checked else False
            self.dataChanged.emit(index, index)
            return True

        if role != qc.Qt.EditRole:
            return False

        if isinstance(current_value, Argument):
            value = Argument(value)

        if isinstance(current_value, list) and not util.are_list_types_homogeneous_and_equal(value, current_value):
            q.QMessageBox.critical(None, 'Bug',
                f'Refusing to set value because the list elements have different data types. Please report this issue.\n\nCurrent value: {current_value}\nNew value: {value}')
            return False

        if not isinstance(value, type(current_value)):
            q.QMessageBox.critical(None, 'Bug',
                f'Refusing to set value because the data type is different (wanted {type(current_value)}, got {type(value)}). Please report this issue.\n\nCurrent value: {current_value}\nNew value: {value}')
            return False

        self.cdata[self.keys[row]] = value
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: qc.QModelIndex, role: qc.Qt.ItemDataRole) -> qc.QVariant:
        col = index.column()
        row = index.row()
        item = self.cdata[self.keys[row]]

        if role == qc.Qt.UserRole:
            return item
        if role == qc.Qt.CheckStateRole:
            if col != ContainerModelColumn.Value or not isinstance(item, bool):
                return qc.QVariant()
            return qc.Qt.Checked if item else qc.Qt.Unchecked
        if role == qc.Qt.EditRole or role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole:
            if col == ContainerModelColumn.Key:
                return self.keys[row]
            if col == ContainerModelColumn.Value:
                if isinstance(item, bool):
                    return qc.QVariant()
                if isinstance(item, ActorIdentifier):
                    return str(item)
                if isinstance(item, Argument):
                    return str(item)
                if isinstance(item, list):
                    return ', '.join(str(i) for i in item)
                return item
            if col == ContainerModelColumn.DataType:
                return util.get_container_value_type(item)

        return qc.QVariant()
