import evfl.evfl
import evfl.actor
import evfl.event
import gzip
import io
import os
import typing
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

def read_flow(path: str, flow: evfl.evfl.EventFlow):
    if path.endswith('.gz'):
        with gzip.open(path, 'rb') as f:
            flow.read(f.read())
    else:
        with open(path, 'rb') as f:
            flow.read(f.read())

def write_flow(path: str, flow: evfl.evfl.EventFlow):
    try:
        if path.endswith('.gz'):
            buf = io.BytesIO()
            flow.write(buf)
            with gzip.open(path + '.tmp', 'wb') as f:
                f.write(buf.getbuffer())
        else:
            with open(path + '.tmp', 'wb') as f:
                flow.write(f)
        os.replace(path + '.tmp', path)
    except:
        try:
            os.unlink(path + '.tmp')
        except FileNotFoundError:
            pass
        raise

def get_path(rel_path: str):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), rel_path)

def get_event_type(event: evfl.event.Event) -> str:
    if isinstance(event.data, evfl.event.ActionEvent):
        return 'Action'
    if isinstance(event.data, evfl.event.SwitchEvent):
        return 'Switch'
    if isinstance(event.data, evfl.event.ForkEvent):
        return 'Fork'
    if isinstance(event.data, evfl.event.JoinEvent):
        return 'Join'
    if isinstance(event.data, evfl.event.SubFlowEvent):
        return 'Sub flow'
    return '???'

def get_event_description(event: evfl.event.Event) -> str:
    if isinstance(event.data, evfl.event.ActionEvent):
        return f'{str(event.data.actor.v.identifier)}::{str(event.data.actor_action.v)}'
    if isinstance(event.data, evfl.event.SwitchEvent):
        return f'{str(event.data.actor.v.identifier)}::{str(event.data.actor_query.v)}'
    if isinstance(event.data, evfl.event.ForkEvent):
        return '–'
    if isinstance(event.data, evfl.event.JoinEvent):
        return '–'
    if isinstance(event.data, evfl.event.SubFlowEvent):
        return f'{event.data.res_flowchart_name}<{event.data.entry_point_name}>'
    return '???'

def get_event_next_summary(event: evfl.event.Event) -> str:
    if isinstance(event.data, evfl.event.ActionEvent) or isinstance(event.data, evfl.event.JoinEvent) or isinstance(event.data, evfl.event.SubFlowEvent):
        return event.data.nxt.v.name if event.data.nxt.v else '–'
    if isinstance(event.data, evfl.event.SwitchEvent):
        return f'{len(event.data.cases)} case(s)'
    if isinstance(event.data, evfl.event.ForkEvent):
        return f'{len(event.data.forks)} fork(s)'
    return '???'

def get_event_param_list(event: evfl.event.Event) -> typing.Dict[str, typing.Any]:
    if isinstance(event.data, evfl.event.ActionEvent) or isinstance(event.data, evfl.event.SwitchEvent) or isinstance(event.data, evfl.event.SubFlowEvent):
        if not event.data.params:
            return dict()
        return event.data.params.data
    return dict()

def get_event_full_description(event: evfl.event.Event) -> str:
    info = [event.name, get_event_type(event), get_event_description(event)]
    return ' - '.join([x for x in info if (x and x != '–')])

def get_container_value_type(value: typing.Any) -> str:
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, str):
        if isinstance(value, evfl.common.Argument):
            return 'argument'
        return 'string'
    if isinstance(value, evfl.common.ActorIdentifier):
        return 'actor id.'
    if isinstance(value, list):
        if isinstance(value[0], bool):
            return 'bools'
        if isinstance(value[0], int):
            return 'ints'
        if isinstance(value[0], float):
            return 'floats'
        if isinstance(value[0], str):
            return 'strings'
    return '???'

def is_valid_container_value_type(value: typing.Any) -> bool:
    return get_container_value_type(value) != '???'

def is_list_homogeneous(l: list) -> bool:
    for i in range(len(l) - 1):
        if type(l[i]) != type(l[i+1]):
            return False
    return True

def are_list_types_homogeneous_and_equal(list1: list, list2: list) -> bool:
    """Check whether both lists contain the same data type and only one."""
    if not (is_list_homogeneous(list1) and is_list_homogeneous(list2)):
        return False
    if list1 and list2 and type(list1[0]) != type(list2[0]):
        return False
    return True

def is_actor_in_use(events: typing.List[evfl.event.Event], actor: evfl.actor.Actor) -> bool:
    for event in events:
        if isinstance(event.data, evfl.event.ActionEvent) or isinstance(event.data, evfl.event.SwitchEvent):
            if event.data.actor.v == actor:
                return True
    return False

def is_actor_string_in_use(events: typing.List[evfl.event.Event], value: evfl.common.StringHolder) -> bool:
    for event in events:
        if isinstance(event.data, evfl.event.ActionEvent):
            if event.data.actor_action.v is value:
                return True
        if isinstance(event.data, evfl.event.SwitchEvent):
            if event.data.actor_query.v is value:
                return True
    return False

def connect_model_change_signals(model, flow_data, reload_flowchart_needed: bool = True) -> None:
    def emit(*_) -> None:
        flow_data.reload_flowchart_needed = reload_flowchart_needed
        flow_data.flowDataChanged.emit()
        flow_data.reload_flowchart_needed = True

    model.dataChanged.connect(emit)
    model.rowsInserted.connect(emit)
    model.rowsRemoved.connect(emit)

class ItemEditorFactory(q.QItemEditorFactory):
    """Reimplements createEditor() to increase precision for doubles.

    Note: this MUST not be set as the default editor factory. Doing so will cause Qt to
    destruct the default factory and stop handling edit events for other simple data types."""
    def createEditor(self, userType, parent):
        if userType == qc.QVariant.Double:
            box = q.QDoubleSpinBox(parent)
            box.setDecimals(5)
            box.setSingleStep(0.1)
            box.setRange(-1000000, 1000000)
            return box
        return super().createEditor(userType, parent)

def set_view_delegate(view) -> None:
    delegate = q.QStyledItemDelegate()
    delegate.setItemEditorFactory(ItemEditorFactory())
    view.setItemDelegate(delegate)
