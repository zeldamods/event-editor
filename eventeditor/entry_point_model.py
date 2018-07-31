import re
import typing

from evfl import EventFlow
from evfl.entry_point import EntryPoint
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class EntryPointModel(qc.QAbstractListModel):
    def __init__(self, *kwargs) -> None:
        super().__init__(*kwargs)
        self.flow: typing.Optional[EventFlow] = None
        self.l: typing.List[EntryPoint] = []

    def append(self, entry_point: EntryPoint) -> bool:
        self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
        self.l.append(entry_point)
        self.endInsertRows()
        return True

    def removeRow(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.l.pop(row)
        self.endRemoveRows()
        return True

    def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
        return qc.Qt.ItemIsEditable | super().flags(index)

    def has(self, name: str) -> bool:
        return any(entry.name == name for entry in self.l)

    def set(self, flow) -> None:
        self.beginResetModel()
        self.flow = flow
        self.l = self.flow.flowchart.entry_points if self.flow and self.flow.flowchart else []
        self.endResetModel()

    def rowCount(self, parent) -> int:
        return len(self.l)

    def setData(self, index: qc.QModelIndex, value, role) -> bool:
        if role != qc.Qt.EditRole or not index.isValid():
            return False
        if not isinstance(value, str) or not value or re.match('^Event(\d)+$', value) is not None or value == '*j32':
            q.QMessageBox.critical(None, 'Cannot rename', f'"{value}" is an invalid entry point name.')
            return False
        if self.l[index.row()].name == value:
            return False
        if self.has(value):
            q.QMessageBox.critical(None, 'Cannot rename', f'"{value}" is already used by another entry point.')
            return False
        self.l[index.row()].name = value
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: qc.QModelIndex, role):
        if role == qc.Qt.UserRole:
            return self.l[index.row()]
        if role == qc.Qt.DisplayRole or role == qc.Qt.EditRole or role == qc.Qt.ToolTipRole:
            return self.l[index.row()].name
        return qc.QVariant()
