import typing

from evfl import EventFlow, Actor
from evfl.common import StringHolder
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ActorStringListModel(qc.QAbstractListModel):
    def __init__(self, parent, l: typing.List[StringHolder]) -> None:
        super().__init__(parent)
        self.l = l

    def set(self, l: typing.List[StringHolder]) -> None:
        self.beginResetModel()
        self.l = l
        self.endResetModel()

    def rowCount(self, parent) -> int:
        return len(self.l)

    def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
        return qc.Qt.ItemIsEditable | super().flags(index)

    def has(self, string: str) -> bool:
        return any(s.v == string for s in self.l)

    def append(self, string: str) -> bool:
        self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
        self.l.append(StringHolder(string))
        self.endInsertRows()
        return True

    def remove(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.l.pop(row)
        self.endRemoveRows()
        return True

    def setData(self, index: qc.QModelIndex, value, role) -> bool:
        if role != qc.Qt.EditRole:
            return False
        row = index.row()
        assert isinstance(value, str)
        self.l[row].v = value
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: qc.QModelIndex, role) -> qc.QVariant:
        row = index.row()
        if role == qc.Qt.UserRole:
            return self.l[row]
        if role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole or role == qc.Qt.EditRole:
            return str(self.l[row])
        return qc.QVariant()
