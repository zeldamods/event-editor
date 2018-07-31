from enum import IntEnum, auto
import typing

from eventeditor.util import *
from evfl import EventFlow, Event
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class EventModelColumn(IntEnum):
    Name = 0
    Type = auto()
    Description = auto()
    Next = auto()

class EventModel(qc.QAbstractTableModel):
    def __init__(self, *kwargs) -> None:
        super().__init__(*kwargs)
        self.flow: typing.Optional[EventFlow] = None
        self.l: list = []

    def append(self, event: Event) -> bool:
        self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
        self.l.append(event)
        self.endInsertRows()
        return True

    def removeRow(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.l.pop(row)
        self.endRemoveRows()
        return True

    def set(self, flow) -> None:
        self.beginResetModel()
        self.flow = flow
        self.l = self.flow.flowchart.events if self.flow and self.flow.flowchart else []
        self.endResetModel()

    def columnCount(self, parent) -> int:
        return len(EventModelColumn)

    def rowCount(self, parent) -> int:
        return len(self.l)

    def headerData(self, section, orientation, role) -> qc.QVariant:
        if role != qc.Qt.DisplayRole:
            return qc.QVariant()

        if section == EventModelColumn.Name:
            return 'Name'
        if section == EventModelColumn.Type:
            return 'Type'
        if section == EventModelColumn.Description:
            return 'Description'
        if section == EventModelColumn.Next:
            return 'Next'
        return 'Unknown'

    def data(self, index, role) -> qc.QVariant:
        col = index.column()
        row = index.row()

        if role == qc.Qt.UserRole:
            return self.l[row]

        if role != qc.Qt.DisplayRole:
            return qc.QVariant()

        if col == EventModelColumn.Name:
            return self.l[row].name
        if col == EventModelColumn.Type:
            return get_event_type(self.l[row])
        if col == EventModelColumn.Description:
            return get_event_description(self.l[row])
        if col == EventModelColumn.Next:
            return get_event_next_summary(self.l[row])
        return qc.QVariant()
