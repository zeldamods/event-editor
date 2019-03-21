from enum import IntEnum, auto
import typing

from eventeditor.actor_model import ActorModelColumn
from eventeditor.actor_string_list_model import ActorStringListModel
from eventeditor.actor_string_list_view import ActorActionListView, ActorQueryListView
from eventeditor.container_model import ContainerModel
from eventeditor.container_view import ContainerView
from eventeditor.flow_data import FlowDataChangeReason
import eventeditor.util as util
from evfl import Container, EventFlow, Actor, ActorIdentifier
from evfl.entry_point import EntryPoint
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ActorEditDialog(q.QDialog):
    def __init__(self, parent, flow_data, idx: int) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Edit actor')
        self.setMinimumWidth(500)
        self.flow_data = flow_data
        self.mapper = q.QDataWidgetMapper(self)
        self.mapper.setSubmitPolicy(q.QDataWidgetMapper.ManualSubmit)
        self.mapper.setModel(flow_data.actor_model)

        self.initWidgets(idx)
        self.initLayout()
        self.connectWidgets()

        self.mapper.setCurrentIndex(idx)
        self.prev_identifier = ActorIdentifier(self.name_edit.text(), self.sub_name_edit.text())

    def initWidgets(self, idx: int) -> None:
        self.form = q.QFormLayout()

        self.name_edit = q.QLineEdit()
        self.form.addRow('&Name:', self.name_edit)
        self.mapper.addMapping(self.name_edit, ActorModelColumn.Name)

        self.sub_name_edit = q.QLineEdit()
        self.form.addRow('S&ub name:', self.sub_name_edit)
        self.mapper.addMapping(self.sub_name_edit, ActorModelColumn.SubName)

        self.arg_group = self.createArgumentGroup()
        model = self.mapper.model()
        ep = model.data(model.createIndex(idx, -1), qc.Qt.UserRole).argument_entry_point.v
        if ep:
            self.arg_group.setChecked(True)
            self.ep_cbox.setCurrentIndex(self.ep_cbox.model().l.index(ep))
        else:
            self.arg_group.setChecked(False)

        self.btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);

    def createArgumentGroup(self) -> q.QGroupBox:
        form = q.QFormLayout()

        self.argument_name_edit = q.QLineEdit()
        form.addRow('Argument name:', self.argument_name_edit)
        self.mapper.addMapping(self.argument_name_edit, ActorModelColumn.ArgumentName)

        self.ep_cbox = q.QComboBox()
        form.addRow('Entry point:', self.ep_cbox)
        self.ep_cbox.setModel(self.flow_data.entry_point_model)
        self.mapper.addMapping(self.ep_cbox, ActorModelColumn.ArgumentEntryPoint, b'currentData')

        group = q.QGroupBox('Is an &argument')
        group.setCheckable(True)
        group.setLayout(form)
        return group

    def initLayout(self) -> None:
        layout = q.QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(self.arg_group)
        layout.addWidget(self.btn_box)

    def connectWidgets(self) -> None:
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

    def accept(self) -> None:
        model = self.mapper.model()
        identifier = ActorIdentifier(self.name_edit.text(), self.sub_name_edit.text())
        if identifier != self.prev_identifier and model.has(identifier):
            q.QMessageBox.critical(self, 'Cannot edit actor', f'{identifier} is already used as an actor identifier. Please pick another one.')
            return

        self.mapper.submit()
        if not self.arg_group.isChecked():
            model.setData(model.createIndex(self.mapper.currentIndex(), ActorModelColumn.ArgumentName), '', qc.Qt.EditRole)
            model.setData(model.createIndex(self.mapper.currentIndex(), ActorModelColumn.ArgumentEntryPoint), None, qc.Qt.EditRole)
        super().accept()

class ActorAddDialog(ActorEditDialog):
    def __init__(self, parent, flow_data, idx) -> None:
        super().__init__(parent, flow_data, idx)
        self.setWindowTitle('Add new actor')

    def reject(self) -> None:
        self.flow_data.actor_model.remove(self.flow_data.actor_model.data(
            self.flow_data.actor_model.createIndex(self.flow_data.actor_model.rowCount(None) - 1, -1),
            qc.Qt.UserRole))
        super().reject()

class ActorDetailPane(q.QWidget):
    jumpToEventsRequested = qc.pyqtSignal(str)

    def __init__(self, parent, flow_data) -> None:
        super().__init__(parent)
        self.flow_data = flow_data
        self.actor: typing.Optional[Actor] = None
        self.action_model = ActorStringListModel(parent, [])
        self.query_model = ActorStringListModel(parent, [])
        self.container_model = ContainerModel(parent)
        self.initWidgets()
        self.initLayout()
        self.connectWidgets()

    def setActor(self, actor: typing.Optional[Actor]) -> None:
        self.actor = actor
        self.action_model.set(self.actor.actions if self.actor else [])
        self.query_model.set(self.actor.queries if self.actor else [])
        if self.actor and not self.actor.params:
            self.actor.params = Container()
        self.container_model.set(self.actor.params if self.actor else None)
        if self.actor:
            self.action_view.setActor(self.actor)
            self.query_view.setActor(self.actor)

    def initWidgets(self) -> None:
        self.action_view = ActorActionListView(self, self.action_model, self.flow_data)
        self.query_view = ActorQueryListView(self, self.query_model, self.flow_data)
        self.container_view = ContainerView(self, self.container_model, self.flow_data)

    def initLayout(self) -> None:
        layout = q.QHBoxLayout(self)

        layout.addWidget(self.action_view, stretch=1)
        layout.addWidget(self.query_view, stretch=1)
        layout.addWidget(self.container_view, stretch=2)
        layout.setContentsMargins(0, 0, 0, 0)

    def connectWidgets(self) -> None:
        util.connect_model_change_signals(self.action_model, self.flow_data, FlowDataChangeReason.Actors)
        util.connect_model_change_signals(self.query_model, self.flow_data, FlowDataChangeReason.Actors)
        util.connect_model_change_signals(self.container_model, self.flow_data, FlowDataChangeReason.Actors)

        self.action_view.addActionBuilder(lambda menu, idx: menu.addAction('&Jump to events', lambda: self.onJumpToEvents(idx)))
        self.query_view.addActionBuilder(lambda menu, idx: menu.addAction('&Jump to events', lambda: self.onJumpToEvents(idx)))
        self.container_view.addActionBuilder(lambda menu, idx: menu.addAction('&Add default create parameters', lambda: self.addDefaultCreateParameters()))

    def addDefaultCreateParameters(self) -> None:
        if not self.actor or not self.actor.params:
            return
        self.actor.params.data.update({'CreateMode': 0, 'IsGrounding': False, 'IsWorld': False, 'PosX': 0.0, 'PosY': 0.0, 'PosZ': 0.0, 'RotX': 0.0, 'RotY': 0.0, 'RotZ': 0.0})
        self.container_model.set(self.actor.params)

    def onJumpToEvents(self, idx) -> None:
        if self.actor:
            self.jumpToEventsRequested.emit(f'{self.actor.identifier}::{idx.data(qc.Qt.UserRole)}')

class ActorView(q.QWidget):
    jumpToActorEventsRequested = qc.pyqtSignal(str)

    def __init__(self, parent, flow_data) -> None:
        super().__init__(parent)
        self.flow_data = flow_data
        self.initWidgets()
        self.initLayout()
        self.connectWidgets()

    def initWidgets(self) -> None:
        self.actor_view = q.QTableView()
        self.actor_view.setModel(self.flow_data.actor_model)
        self.actor_view.verticalHeader().hide()
        self.actor_view.setSelectionBehavior(q.QAbstractItemView.SelectRows)
        self.actor_view.setSelectionMode(q.QAbstractItemView.SingleSelection)
        self.actor_view.horizontalHeader().setSectionResizeMode(q.QHeaderView.ResizeToContents)
        self.actor_view.horizontalHeader().setSectionResizeMode(0, q.QHeaderView.Stretch)
        self.actor_view.horizontalHeader().setSectionResizeMode(1, q.QHeaderView.Stretch)
        self.actor_view.setEditTriggers(q.QAbstractItemView.NoEditTriggers);
        self.actor_view.setContextMenuPolicy(qc.Qt.CustomContextMenu)
        self.actor_view.customContextMenuRequested.connect(self.onContextMenu)

        self.detail_pane = ActorDetailPane(None, self.flow_data)

        self.top_box = q.QHBoxLayout()
        self.top_box.setContentsMargins(5,5,5,0)
        self.num_actors_label = q.QLabel()
        self.top_box.addWidget(self.num_actors_label, stretch=1)
        self.add_actor_btn = q.QPushButton('A&dd...')
        self.add_actor_btn.setEnabled(False)
        self.top_box.addWidget(self.add_actor_btn)

    def initLayout(self) -> None:
        splitter = q.QSplitter(qc.Qt.Vertical)
        splitter.addWidget(self.actor_view)
        self.stacked_pane = q.QStackedWidget()
        self.stacked_pane.addWidget(q.QWidget())
        self.stacked_pane.addWidget(self.detail_pane)
        splitter.addWidget(self.stacked_pane)
        splitter.setSizes([splitter.height() * 0.6, splitter.height() * 0.4])
        layout = q.QVBoxLayout(self)
        layout.addLayout(self.top_box)
        layout.addWidget(splitter, stretch=1)
        layout.setContentsMargins(0, 0, 0, 0)

    def connectWidgets(self) -> None:
        self.add_actor_btn.clicked.connect(self.addActor)
        self.flow_data.fileLoaded.connect(lambda: self.add_actor_btn.setEnabled(True))
        self.flow_data.fileLoaded.connect(lambda: self.hideActorDetailPane())
        self.flow_data.flowDataChanged.connect(self.updateNumActorLabel)
        self.updateNumActorLabel()

        self.actor_view.doubleClicked.connect(self.editActor)
        self.actor_view.selectionModel().currentRowChanged.connect(self.onCurrentChanged)
        self.actor_view.selectionModel().selectionChanged.connect(self.onSelectionChanged)

    def updateNumActorLabel(self, *_) -> None:
        self.num_actors_label.setText(f'{self.flow_data.actor_model.rowCount(None)} actor(s)')

    def addActor(self) -> None:
        ok = self.flow_data.actor_model.appendEmptyActor()
        assert ok
        dialog = ActorAddDialog(self, self.flow_data, self.flow_data.actor_model.rowCount(None) - 1)
        dialog.exec_()

    def editActor(self, idx: qc.QModelIndex) -> None:
        dialog = ActorEditDialog(self, self.flow_data, idx.row())
        dialog.exec_()

    def removeActor(self, idx: qc.QModelIndex) -> None:
        actor = idx.data(qc.Qt.UserRole)
        if util.is_actor_in_use(self.flow_data.flow.flowchart.events, actor):
            q.QMessageBox.critical(self, 'Cannot remove actor', f'{actor.identifier} cannot be removed because it is used by events. Please remove any references to this actor and try again.')
            return

        self.flow_data.actor_model.remove(actor)

    def hideActorDetailPane(self) -> None:
        self.detail_pane.setActor(None)
        self.stacked_pane.setCurrentIndex(0)

    def onCurrentChanged(self, current, previous) -> None:
        if previous.row() == -1:
            self.hideActorDetailPane()

    def onSelectionChanged(self, selected, deselected) -> None:
        if len(selected.indexes()) != len(ActorModelColumn):
            self.hideActorDetailPane()
            return

        self.detail_pane.setActor(selected.indexes()[0].data(qc.Qt.UserRole))
        self.stacked_pane.setCurrentIndex(1)

    def onContextMenu(self, pos) -> None:
        smodel = self.actor_view.selectionModel()
        if not smodel.hasSelection():
            return

        idx = smodel.selectedRows()[0]

        menu = q.QMenu()
        menu.addAction('&Edit...', lambda: self.editActor(idx))
        menu.addAction('&Remove', lambda: self.removeActor(idx))
        menu.addAction('&Jump to events', lambda: self.jumpToActorEventsRequested.emit(str(idx.data(qc.Qt.UserRole).identifier) + '::'))
        menu.exec_(self.sender().viewport().mapToGlobal(pos))
