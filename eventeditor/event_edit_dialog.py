import copy
import typing

import eventeditor.ai as ai
from eventeditor.actor_string_list_model import ActorStringListModel
from eventeditor.container_model import ContainerModel
from eventeditor.container_view import ContainerView
from eventeditor.flow_data import FlowData
import eventeditor.util as util
from evfl import Container, Actor, Event
from evfl.enums import EventType
import evfl.event
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ActorProxyModel(qc.QIdentityProxyModel):
    def data(self, index, role):
        if index.column() == 0 and role == qc.Qt.DisplayRole:
            return str(self.sourceModel().data(index, qc.Qt.UserRole).identifier)
        return super().data(index, role)

class ActorRelatedEventEditDialog(q.QDialog):
    def __init__(self, parent, flow_data: FlowData, idx: int, attr_list_name: str, attr_name: str) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Edit event')
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.flow_data = flow_data
        self.event = self.flow_data.event_model.createIndex(idx, 0).data(qc.Qt.UserRole)
        assert isinstance(self.event.data, evfl.event.ActionEvent) or isinstance(self.event.data, evfl.event.SwitchEvent)
        self.is_switch = isinstance(self.event.data, evfl.event.SwitchEvent)
        self.attr_list_name = attr_list_name
        self.attr_name = attr_name

        if self.is_switch:
            self.setWindowTitle('Edit switch event')
        else:
            self.setWindowTitle('Edit action event')

        self.param_model = ContainerModel(self)
        if not self.event.data.params:
            self.event.data.params = Container()
        self.modified_params: Container = copy.deepcopy(self.event.data.params)
        self.param_model.set(self.modified_params)
        self.attr_model = ActorStringListModel(self, [])
        util.connect_model_change_signals(self.attr_model, self.flow_data)

        self.createActorCbox()
        self.createAttrCbox()
        self.createParametersView()

        row = q.QHBoxLayout()
        row.addWidget(self.actor_cbox, stretch=1)
        separator = q.QLabel('::')
        row.addWidget(separator)
        row.addWidget(self.attr_cbox, stretch=1)

        layout = q.QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.param_view)
        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def createActorCbox(self) -> None:
        self.actor_proxy_model = ActorProxyModel(self)
        self.actor_proxy_model.setSourceModel(self.flow_data.actor_model)
        self.actor_cbox = q.QComboBox()
        self.actor_cbox.currentIndexChanged.connect(self.onActorSelected)
        self.actor_cbox.setModel(self.actor_proxy_model)
        actor = self.event.data.actor.v
        self.actor_cbox.setCurrentIndex(self.actor_cbox.findData(actor))

    def createAttrCbox(self) -> None:
        self.attr_cbox = q.QComboBox()
        self.attr_cbox.setModel(self.attr_model)
        attr = getattr(self.event.data, self.attr_name).v
        self.attr_cbox.setCurrentIndex(self.attr_cbox.findData(attr))

    def createParametersView(self) -> None:
        self.param_view = ContainerView(None, self.param_model, self.flow_data, has_autofill_btn=True)
        self.param_view.autofillRequested.connect(self.onAutofillRequested)

    def onAutofillRequested(self) -> None:
        new_actor: Actor = self.actor_cbox.currentData()
        new_attr: str = self.attr_cbox.currentData().v if self.attr_cbox.currentData() else ''
        if not new_actor or not new_attr:
            q.QMessageBox.critical(self, 'Cannot auto fill', 'Please select an actor and a function.')
            return

        aiprog = ai.load_aiprog(new_actor.identifier.name)
        if not aiprog:
            q.QMessageBox.critical(self, 'Cannot auto fill', 'Failed to load the actor AI program')
            return

        actual_ai_class: typing.Optional[str] = None
        if self.is_switch:
            actual_ai_class = aiprog.queries.get(new_attr, None)
        else:
            actual_ai_class = aiprog.actions.get(new_attr, None)

        if actual_ai_class is None:
            q.QMessageBox.critical(self, 'Cannot auto fill', 'The selected action/query is not registered in the AI program.')
            return

        ai_type = ai.AIType.Query if self.is_switch else ai.AIType.Action
        parameters = ai.ai_def_instance.get_parameters(ai_type, actual_ai_class)

        self.modified_params.data.clear()
        if not self.is_switch:
            self.modified_params.data['IsWaitFinish'] = False
        for param in parameters:
            self.modified_params.data[param.name] = param.get_default_value()

        self.param_model.set(self.modified_params)

    def onActorSelected(self, actor_idx: int) -> None:
        if actor_idx == -1:
            return
        self.attr_model.set(getattr(self.actor_cbox.currentData(), self.attr_list_name))

    def accept(self) -> None:
        new_actor = self.actor_cbox.currentData()
        new_attr = self.attr_cbox.currentData()
        if not new_actor or not new_attr:
            q.QMessageBox.critical(self, 'Invalid data', 'Please select an actor and a function.')
            return

        previous_actor = self.event.data.actor.v
        previous_attr = getattr(self.event.data, self.attr_name).v
        self.event.data.actor.v = new_actor
        attr = getattr(self.event.data, self.attr_name)
        attr.v = new_attr

        self.event.data.params = self.modified_params

        self.flow_data.reload_flowchart_needed = previous_actor != new_actor or previous_attr != new_attr
        self.flow_data.flowDataChanged.emit()
        super().accept()

class SubFlowEventEditDialog(q.QDialog):
    def __init__(self, parent, flow_data: FlowData, idx: int) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Edit event')
        self.setMinimumWidth(500)
        self.flow_data = flow_data
        self.event = self.flow_data.event_model.createIndex(idx, 0).data(qc.Qt.UserRole)
        assert self.flow_data.flow and isinstance(self.event.data, evfl.event.SubFlowEvent)
        self.param_model = ContainerModel(self)
        if not self.event.data.params:
            self.event.data.params = Container()
        self.modified_params = copy.deepcopy(self.event.data.params)
        self.param_model.set(self.modified_params)

        form = q.QFormLayout()

        self.flowchart_ledit = q.QLineEdit()
        self.flowchart_ledit.setText(self.event.data.res_flowchart_name)
        self.flowchart_ledit.setPlaceholderText('Flowchart name (optional)')
        form.addRow('&Flowchart:', self.flowchart_ledit)
        self.entry_point_ledit = q.QLineEdit()
        self.entry_point_ledit.setText(self.event.data.entry_point_name)
        self.entry_point_ledit.setPlaceholderText('Entry point name (mandatory)')
        form.addRow('&Entry point:', self.entry_point_ledit)

        help_msg = q.QLabel(f'Note: this flowchart ({self.flow_data.flow.name}) will be used if no flowchart is explicitly specified.')

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(help_msg)
        layout.addWidget(ContainerView(None, self.param_model, self.flow_data))
        layout.addWidget(btn_box)

    def accept(self) -> None:
        new_flowchart = self.flowchart_ledit.text()
        new_ep = self.entry_point_ledit.text()
        if not new_ep:
            q.QMessageBox.critical(self, 'Invalid data', 'The entry point name cannot be empty.')
            return

        self.event.data.params = self.modified_params

        prev_flowchart = self.event.data.res_flowchart_name
        prev_ep = self.event.data.entry_point_name
        self.event.data.res_flowchart_name = new_flowchart
        self.event.data.entry_point_name = new_ep

        self.flow_data.reload_flowchart_needed = prev_flowchart != new_flowchart or prev_ep != new_ep
        self.flow_data.flowDataChanged.emit()
        super().accept()

def make_event_edit_dialog(parent, flow_data: FlowData, idx: int) -> typing.Optional[q.QDialog]:
    model = flow_data.event_model
    event = flow_data.event_model.data(model.createIndex(idx, 0), qc.Qt.UserRole)
    if isinstance(event.data, evfl.event.ActionEvent):
        return ActorRelatedEventEditDialog(parent, flow_data, idx, 'actions', 'actor_action')
    if isinstance(event.data, evfl.event.SwitchEvent):
        return ActorRelatedEventEditDialog(parent, flow_data, idx, 'queries', 'actor_query')
    if isinstance(event.data, evfl.event.SubFlowEvent):
        return SubFlowEventEditDialog(parent, flow_data, idx)
    return None

def show_event_editor(parent, flow_data: FlowData, idx: int) -> bool:
    dialog = make_event_edit_dialog(parent, flow_data, idx)
    if dialog:
        dialog.exec_()
        return True

    q.QMessageBox.information(parent, 'Edit event', 'This event has no editable property.')
    return False
