from enum import IntEnum, auto
import typing

from eventeditor.event_chooser_dialog import EventChooserDialog
from eventeditor.flow_data import FlowData
import eventeditor.util as util
from evfl import Event
from evfl.common import RequiredIndex
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

_Cases = typing.Dict[int, RequiredIndex[Event]]
_Forks = typing.List[RequiredIndex[Event]]

_PLACEHOLDER_EVENT = Event()
_PLACEHOLDER_EVENT.name = '<placeholder>'

class EventBranchEditorTableView(q.QTableView):
    chooserEventDoubleClicked = qc.pyqtSignal(int)
    chooserSelectSignal = qc.pyqtSignal(int)
    actionProhibitionChanged = qc.pyqtSignal(bool)

    def __init__(self, parent, flow_data: FlowData) -> None:
        super().__init__(parent)
        self.flow_data = flow_data

    def edit(self, index: qc.QModelIndex, trigger, event) -> bool:
        if not (self.editTriggers() & trigger) or not index.isValid() or not (index.flags() & (qc.Qt.ItemIsEditable | qc.Qt.ItemIsUserCheckable)):
            return False

        data = index.data(qc.Qt.EditRole)
        if isinstance(data, Event):
            self.actionProhibitionChanged.emit(True)
            dialog = EventChooserDialog(self, self.flow_data, enable_ctx_menu=False)
            dialog.show()
            self.chooserSelectSignal.connect(dialog.event_view.selectEvent)
            try:
                dialog.event_view.selectEvent(self.flow_data.flow.flowchart.events.index(data))
            except ValueError:
                pass
            dialog.event_view.jumpToFlowchartRequested.connect(self.chooserEventDoubleClicked)
            dialog.finished.connect(lambda: self.actionProhibitionChanged.emit(False))
            def onChooserAccept():
                selected_event = dialog.getSelectedEvent()
                self.model().setData(index, selected_event, qc.Qt.EditRole)
            dialog.accepted.connect(onChooserAccept)
            return False

        return super().edit(index, trigger, event)

class SwitchCase:
    __slots__ = ('value', 'event')
    def __init__(self, value: int, event: Event) -> None:
        self.value = value
        self.event = event

class SwitchCaseModelColumn(IntEnum):
    Value = 0
    Event = auto()

class SwitchCaseModel(qc.QAbstractTableModel):
    def __init__(self, parent, cases: _Cases) -> None:
        super().__init__(parent)
        self.setCases(cases)

    def isValid(self) -> bool:
        for i in range(len(self.l)):
            if self.l[i].event is _PLACEHOLDER_EVENT:
                return False
            if i != len(self.l) - 1 and self.l[i].value == self.l[i + 1].value:
                return False
        return True

    def updateCaseDict(self, case_dict: _Cases) -> None:
        case_dict.clear()
        for case in sorted(self.l, key=lambda c: c.value):
            idx: RequiredIndex[Event] = RequiredIndex()
            idx.v = case.event
            case_dict[case.value] = idx

    def setCases(self, cases: _Cases) -> None:
        self.beginResetModel()
        self.l: typing.List[SwitchCase] = []
        for value, event_idx in cases.items():
            self.l.append(SwitchCase(value, event_idx.v))
        self.endResetModel()

    def columnCount(self, parent):
        return len(SwitchCaseModelColumn)

    def rowCount(self, parent):
        return len(self.l)

    def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
        return qc.Qt.ItemIsEditable | super().flags(index)

    def hasCaseValue(self, value: int) -> bool:
        return any(case.value == value for case in self.l)

    def appendCase(self, case: SwitchCase) -> bool:
        if self.hasCaseValue(case.value):
            q.QMessageBox.critical(None, 'Invalid data', f'Value {case.value} is already handled by another case.')
            return False
        self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
        self.l.append(case)
        self.endInsertRows()
        return True

    def removeCase(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.l.pop(row)
        self.endRemoveRows()
        return True

    def setData(self, index: qc.QModelIndex, value, role) -> bool:
        if role != qc.Qt.EditRole:
            return False
        col = index.column()
        row = index.row()
        if self.l[row].value == value:
            return True
        if col == SwitchCaseModelColumn.Value and isinstance(value, int):
            if self.hasCaseValue(value):
                q.QMessageBox.critical(None, 'Invalid data', f'Value {value} is already handled by another case.')
                return False
            self.l[row].value = value
        elif col == SwitchCaseModelColumn.Event and isinstance(value, Event):
            self.l[row].event = value
        else:
            return False
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: qc.QModelIndex, role) -> typing.Any:
        col = index.column()
        row = index.row()
        if role == qc.Qt.UserRole:
            return self.l[row]
        if role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole or role == qc.Qt.EditRole:
            if col == SwitchCaseModelColumn.Value:
                return self.l[row].value
            if col == SwitchCaseModelColumn.Event:
                event = self.l[row].event
                if role == qc.Qt.EditRole:
                    return event
                if event is _PLACEHOLDER_EVENT:
                    return '<placeholder>'
                return f'{util.get_event_full_description(event)}'
        return qc.QVariant()

    def headerData(self, section, orientation, role) -> qc.QVariant:
        if role != qc.Qt.DisplayRole:
            return qc.QVariant()
        if section == SwitchCaseModelColumn.Value:
            return 'Value'
        if section == SwitchCaseModelColumn.Event:
            return 'Event'
        return 'Unknown'

class SwitchEventEditDialog(q.QDialog):
    chooserEventDoubleClicked = qc.pyqtSignal(int)
    chooserSelectSignal = qc.pyqtSignal(int)

    def __init__(self, parent, cases: _Cases, flow_data: FlowData) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit switch event')
        self.setMinimumWidth(600)
        self.flow_data = flow_data
        self.orig_cases = cases
        self.model = SwitchCaseModel(self, cases)

        self.tview = EventBranchEditorTableView(None, self.flow_data)
        self.tview.setModel(self.model)
        self.tview.verticalHeader().hide()
        self.tview.setSelectionBehavior(q.QAbstractItemView.SelectRows)
        self.tview.setSelectionMode(q.QAbstractItemView.SingleSelection)
        self.tview.horizontalHeader().setMinimumSectionSize(80)
        self.tview.horizontalHeader().setSectionResizeMode(q.QHeaderView.ResizeToContents)
        self.tview.horizontalHeader().setSectionResizeMode(1, q.QHeaderView.Stretch)
        self.tview.setContextMenuPolicy(qc.Qt.CustomContextMenu)
        self.tview.customContextMenuRequested.connect(self.onContextMenu)
        self.tview.chooserEventDoubleClicked.connect(self.chooserEventDoubleClicked)
        self.chooserSelectSignal.connect(self.tview.chooserSelectSignal)

        add_btn_box = q.QHBoxLayout()
        add_btn = q.QPushButton('Add case')
        add_btn.clicked.connect(self.addCase)
        add_btn_box.addStretch()
        add_btn_box.addWidget(add_btn)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addWidget(self.tview)
        layout.addLayout(add_btn_box)
        layout.addWidget(btn_box)

        self.tview.actionProhibitionChanged.connect(lambda v: self.setEnabled(not v))

    def closeEvent(self, event):
        if not self.isEnabled():
            event.ignore()

    def accept(self) -> None:
        if not self.model.isValid():
            q.QMessageBox.critical(self, 'Invalid data', 'Please ensure there are no placeholder or duplicate cases left.')
            return

        self.model.updateCaseDict(self.orig_cases)
        self.flow_data.flowDataChanged.emit()
        super().accept()

    def addCase(self) -> None:
        value, ok = q.QInputDialog.getInt(self, 'Add new switch case', 'Please enter the case value:')
        if not ok:
            return
        self.model.appendCase(SwitchCase(value, _PLACEHOLDER_EVENT))

    def onContextMenu(self, pos) -> None:
        smodel = self.tview.selectionModel()
        if not smodel.hasSelection():
            return
        sidx = smodel.selectedRows()[0]
        menu = q.QMenu()
        menu.addAction('Remove', lambda: self.model.removeCase(sidx.row()))
        menu.exec_(self.sender().viewport().mapToGlobal(pos))

class ForkEventModel(qc.QAbstractListModel):
    def __init__(self, parent, forks: _Forks) -> None:
        super().__init__(parent)
        self.setForks(forks)

    def isValid(self) -> bool:
        for i in range(len(self.l)):
            if self.l[i] is _PLACEHOLDER_EVENT:
                return False
            if i != len(self.l) - 1 and self.l[i] == self.l[i + 1]:
                return False
        return True

    def updateForkList(self, fork_list: _Forks) -> None:
        fork_list.clear()
        for fork in self.l:
            idx: RequiredIndex[Event] = RequiredIndex()
            idx.v = fork
            fork_list.append(idx)

    def setForks(self, forks: _Forks) -> None:
        self.beginResetModel()
        self.l: typing.List[Event] = []
        for event_idx in forks:
            self.l.append(event_idx.v)
        self.endResetModel()

    def rowCount(self, parent):
        return len(self.l)

    def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
        return qc.Qt.ItemIsEditable | super().flags(index)

    def hasFork(self, fork: Event) -> bool:
        return any(f == fork for f in self.l)

    def appendFork(self, fork: Event) -> bool:
        if self.hasFork(fork):
            q.QMessageBox.critical(None, 'Invalid data', f'{fork.name} is already a fork branch.')
            return False
        self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
        self.l.append(fork)
        self.endInsertRows()
        return True

    def removeCase(self, row: int) -> bool:
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.l.pop(row)
        self.endRemoveRows()
        return True

    def setData(self, index: qc.QModelIndex, value, role) -> bool:
        if role != qc.Qt.EditRole:
            return False
        if self.l[index.row()] == value:
            return True
        if isinstance(value, Event):
            self.l[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def data(self, index: qc.QModelIndex, role) -> typing.Any:
        row = index.row()
        if role == qc.Qt.UserRole:
            return self.l[row]
        if role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole or role == qc.Qt.EditRole:
            event = self.l[row]
            if role == qc.Qt.EditRole:
                return event
            if event is _PLACEHOLDER_EVENT:
                return '<placeholder>'
            return f'{util.get_event_full_description(event)}'
        return qc.QVariant()

# This is pretty similar to the switch edit dialog.
# TODO: refactor and deduplicate this
class ForkEventEditDialog(q.QDialog):
    chooserEventDoubleClicked = qc.pyqtSignal(int)
    chooserSelectSignal = qc.pyqtSignal(int)

    def __init__(self, parent, forks: _Forks, flow_data: FlowData) -> None:
        super().__init__(parent)
        self.setWindowTitle('Edit fork event')
        self.setMinimumWidth(600)
        self.flow_data = flow_data
        self.orig_forks = forks
        self.model = ForkEventModel(self, forks)

        self.tview = EventBranchEditorTableView(None, self.flow_data)
        self.tview.setModel(self.model)
        self.tview.horizontalHeader().hide()
        self.tview.verticalHeader().hide()
        self.tview.setSelectionBehavior(q.QAbstractItemView.SelectRows)
        self.tview.setSelectionMode(q.QAbstractItemView.SingleSelection)
        self.tview.horizontalHeader().setSectionResizeMode(q.QHeaderView.Stretch)
        self.tview.setContextMenuPolicy(qc.Qt.CustomContextMenu)
        self.tview.customContextMenuRequested.connect(self.onContextMenu)
        self.tview.chooserEventDoubleClicked.connect(self.chooserEventDoubleClicked)
        self.chooserSelectSignal.connect(self.tview.chooserSelectSignal)

        add_btn_box = q.QHBoxLayout()
        add_btn = q.QPushButton('Add fork')
        add_btn.clicked.connect(self.addFork)
        add_btn_box.addStretch()
        add_btn_box.addWidget(add_btn)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addWidget(self.tview)
        layout.addLayout(add_btn_box)
        layout.addWidget(btn_box)

        self.tview.actionProhibitionChanged.connect(lambda v: self.setEnabled(not v))

    def closeEvent(self, event):
        if not self.isEnabled():
            event.ignore()

    def accept(self) -> None:
        if not self.model.isValid():
            q.QMessageBox.critical(self, 'Invalid data', 'Please ensure there are no placeholder or duplicate forks left.')
            return

        if self.model.rowCount(qc.QModelIndex()) == 0:
            q.QMessageBox.critical(self, 'Invalid data', 'Fork events must always have at least one branch.')
            return

        self.model.updateForkList(self.orig_forks)
        self.flow_data.flowDataChanged.emit()
        super().accept()

    def addFork(self) -> None:
        self.model.appendFork(_PLACEHOLDER_EVENT)

    def onContextMenu(self, pos) -> None:
        smodel = self.tview.selectionModel()
        if not smodel.hasSelection():
            return
        sidx = smodel.selectedRows()[0]
        menu = q.QMenu()
        menu.addAction('Remove', lambda: self.model.removeCase(sidx.row()))
        menu.exec_(self.sender().viewport().mapToGlobal(pos))
