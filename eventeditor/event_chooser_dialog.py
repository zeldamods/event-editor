from collections import defaultdict
import copy
import typing

from eventeditor.event_view import EventView
from eventeditor.flow_data import FlowData
import eventeditor.util as util
from evfl import Actor, Container, Event, ActionEvent, SwitchEvent, ForkEvent, JoinEvent, SubFlowEvent
from evfl.common import StringHolder
from evfl.enums import EventType
import evfl.event
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class EventTypeChooserDialog(q.QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Choose an event type')

        self.rbtn_group = q.QButtonGroup()
        action_rbtn = q.QRadioButton('&Action')
        action_rbtn.setChecked(True)
        self.rbtn_group.addButton(action_rbtn, EventType.kAction)
        switch_rbtn = q.QRadioButton('&Switch')
        self.rbtn_group.addButton(switch_rbtn, EventType.kSwitch)
        subflow_rbtn = q.QRadioButton('S&ub flow')
        self.rbtn_group.addButton(subflow_rbtn, EventType.kSubFlow)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Ok | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addWidget(action_rbtn)
        layout.addWidget(switch_rbtn)
        layout.addWidget(subflow_rbtn)
        layout.addWidget(btn_box)

    def getChoice(self) -> EventType:
        return self.rbtn_group.checkedId()

def show_event_type_chooser(parent) -> typing.Optional[EventType]:
    dialog = EventTypeChooserDialog(parent)
    if dialog.exec_():
        return dialog.getChoice()
    return None

_placeholder_warning_shown = False
_PLACEHOLDER_ACTOR = Actor()
_PLACEHOLDER_ACTOR.identifier.name = '<placeholder actor>'
_PLACEHOLDER_ACTOR.actions.append(StringHolder('<placeholder action>'))
_PLACEHOLDER_ACTOR.queries.append(StringHolder('<placeholder query>'))

def add_new_event(parent, flow_data: FlowData) -> typing.Optional[Event]:
    etype = show_event_type_chooser(parent)
    if etype is None:
        return None
    new_event = Event()
    new_event.name = flow_data.generateEventName()
    if etype == EventType.kAction:
        new_event.data = ActionEvent()
        new_event.data.actor.v = _PLACEHOLDER_ACTOR
        new_event.data.actor_action.v = _PLACEHOLDER_ACTOR.actions[0]
    elif etype == EventType.kSwitch:
        new_event.data = SwitchEvent()
        new_event.data.actor.v = _PLACEHOLDER_ACTOR
        new_event.data.actor_query.v = _PLACEHOLDER_ACTOR.queries[0]
    elif etype == EventType.kSubFlow:
        new_event.data = SubFlowEvent()
        new_event.data.entry_point_name = 'placeholder sub flow'

    global _placeholder_warning_shown
    if not _placeholder_warning_shown:
        q.QMessageBox.warning(parent, 'Save warning', 'Saves and auto-saves will not work until the placeholder events are edited.')
        _placeholder_warning_shown = True

    flow_data.event_model.append(new_event)
    return new_event

class EventChooserDialog(q.QDialog):
    def __init__(self, parent, flow_data: FlowData, enable_ctx_menu: bool=True) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Choose an event')
        self.setMinimumWidth(700)
        self.setMinimumHeight(250)
        self.flow_data = flow_data

        self.event_view = EventView(None, self.flow_data, enable_ctx_menu)

        add_event_box = q.QHBoxLayout()
        add_event_btn = q.QPushButton('Add event...')
        add_event_btn.clicked.connect(self.addEvent)
        add_event_box.addStretch()
        add_event_box.addWidget(add_event_btn)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Ok | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addWidget(self.event_view)
        layout.addLayout(add_event_box)
        layout.addWidget(btn_box)

    def addEvent(self) -> None:
        if not self.flow_data.flow or not self.flow_data.flow.flowchart:
            return
        new_event = add_new_event(self, self.flow_data)
        if not new_event:
            return
        qc.QTimer.singleShot(1000, lambda:
            self.event_view.selectEvent(self.flow_data.flow.flowchart.events.index(new_event)))

    def accept(self) -> None:
        selected_event = self.event_view.getSelectedEvent()
        if not selected_event:
            q.QMessageBox.critical(self, 'Events', 'Please select an event.')
            return

        self.selected_event = selected_event
        super().accept()

    def getSelectedEvent(self) -> Event:
        return self.selected_event

class CheckableEventParentListModel(qc.QAbstractListModel):
    def __init__(self, parent, child_event: Event, events: typing.List[Event]) -> None:
        super().__init__(parent)
        self.entries: typing.List[typing.Tuple[Event, typing.Any]] = []
        for event in events:
            if isinstance(event.data, SwitchEvent):
                for case, target in event.data.cases.items():
                    if target.v == child_event:
                        self.entries.append((event, case))
            elif isinstance(event.data, ForkEvent):
                for fork in event.data.forks:
                    if fork.v == child_event:
                        self.entries.append((event, fork))
            else:
                self.entries.append((event, None))

        self.is_selected = [True] * len(self.entries)

    def getSelectedEvents(self) -> typing.List[typing.Tuple[Event, typing.List[typing.Any]]]:
        d: typing.DefaultDict[Event, typing.List[typing.Any]] = defaultdict(list)
        for (event, branch), selected in zip(self.entries, self.is_selected):
            if not selected:
                continue
            d[event].append(branch)
        return list(d.items())

    def selectAll(self) -> None:
        self.is_selected = [True] * len(self.entries)
        if self.entries:
            self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(len(self.entries) - 1, 0))

    def selectNone(self) -> None:
        self.is_selected = [False] * len(self.entries)
        if self.entries:
            self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(len(self.entries) - 1, 0))

    def rowCount(self, parent) -> int:
        return len(self.entries)

    def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
        return qc.Qt.ItemIsUserCheckable | super().flags(index)

    def setData(self, index: qc.QModelIndex, value, role) -> bool:
        if role != qc.Qt.CheckStateRole:
            return False
        row = index.row()
        self.is_selected[index.row()] = True if value == qc.Qt.Checked else False
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: qc.QModelIndex, role) -> qc.QVariant:
        row = index.row()
        if role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole:
            description = util.get_event_full_description(self.entries[row][0])
            branch = self.entries[row][1]
            if branch is not None:
                if isinstance(branch, int):
                    description += f' - Case {branch}'
                else:
                    description += f' - Branch: {branch.v.name}'
            return description
        if role == qc.Qt.CheckStateRole:
            return qc.Qt.Checked if self.is_selected[row] else qc.Qt.Unchecked
        return qc.QVariant()

class CheckableEventParentListWidget(q.QWidget):
    def __init__(self, parent, child_event: Event, events: typing.List[Event]) -> None:
        super().__init__(parent)
        self.model = CheckableEventParentListModel(self, child_event, events)

        select_btn_box = q.QHBoxLayout()
        all_btn = q.QPushButton('All')
        all_btn.clicked.connect(lambda: self.model.selectAll())
        none_btn = q.QPushButton('None')
        none_btn.clicked.connect(lambda: self.model.selectNone())
        select_btn_box.addStretch()
        select_btn_box.addWidget(all_btn)
        select_btn_box.addWidget(none_btn)

        self.view = q.QListView()
        self.view.setModel(self.model)

        layout = q.QVBoxLayout(self)
        layout.addLayout(select_btn_box)
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

    def getSelectedEvents(self) -> typing.List[typing.Tuple[Event, typing.List[typing.Any]]]:
        return self.model.getSelectedEvents()
