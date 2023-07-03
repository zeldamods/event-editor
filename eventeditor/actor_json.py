from enum import IntEnum
import typing

from evfl.event import ActionEvent, SwitchEvent
import json
from pathlib import Path
import PyQt5.QtWidgets as q

_actor_definitions_path: typing.Optional[Path] = None
def set_actor_definitions_path(p: typing.Optional[str]) -> None:
    if p:
        global _actor_definitions_path
        _actor_definitions_path = Path(p)

class EventType(IntEnum):
    Action = 0
    Query = 1

def load_actor_json(actor_name: str) -> typing.Dict[str, typing.Any]:
    if not _actor_definitions_path:
        return None

    try:
        # First look for individual actor file (overrides; for power users)
        with open(_actor_definitions_path.parent/f'{actor_name}.json', 'rt') as file:
            return json.loads(file.read())
    except:
        try:
            # Otherwise look in actor definitions file
            with open(_actor_definitions_path, 'rt') as file:
                return json.loads(file.read())[actor_name]
        except:
            return None

def load_event_parameters(actor_name: str, event_name: str, event_type: EventType) -> typing.Dict[str, typing.Any]:
    try:
        actor = load_actor_json(actor_name)

        if event_type == EventType.Action:
            return actor['actions'][event_name]
        if event_type == EventType.Query:
            return actor['queries'][event_name]
        return None
    except:
        return None

def load_actions(actor_name: str) -> typing.Iterable[str]:
    try:
        return load_actor_json(actor_name)['actions'].keys()
    except:
        return None

def load_queries(actor_name: str) -> typing.Iterable[str]:
    try:
        return load_actor_json(actor_name)['queries'].keys()
    except:
        return None

def export_definitions(flow, widget) -> None:
    if not flow:
        q.QMessageBox.information(widget, 'Export actor definition data', 'Open an event flow first')
        return

    if not _actor_definitions_path:
        set_actor_definitions_path(q.QFileDialog.getSaveFileName(widget, 'Export actor definitions to...',  'actor_definitions', 'JSON (*.json)')[0])

    if not _actor_definitions_path:
        return

    try:
        with open(_actor_definitions_path, 'rt') as file:
            definitions = json.loads(file.read())
    except:
        definitions = dict()
    
    for actor in flow.flowchart.actors:
        if actor.identifier.name not in definitions:
            definitions[actor.identifier.name] = {}

        if 'actions' not in definitions[actor.identifier.name]:
            definitions[actor.identifier.name]['actions'] = {}        
        for action in actor.actions:
            if action.v not in definitions[actor.identifier.name]['actions']:
                definitions[actor.identifier.name]['actions'][action.v] = {}

        if 'queries' not in definitions[actor.identifier.name]:
            definitions[actor.identifier.name]['queries'] = {}
        for query in actor.queries:
            if query.v not in definitions[actor.identifier.name]['queries']:
                definitions[actor.identifier.name]['queries'][query.v] = {}
        
        #! Potential future addition: support actor parameters + autofill

    for event in flow.flowchart.events:
        if isinstance(event.data, ActionEvent):
            json_parent = definitions[event.data.actor.v.identifier.name]['actions']
            event_key = event.data.actor_action.v.v
        elif isinstance(event.data, SwitchEvent):
            json_parent = definitions[event.data.actor.v.identifier.name]['queries']
            event_key = event.data.actor_query.v.v
        else:
            # Skip subflows
            continue

        if event_key not in json_parent:
            # Shouldn't be reachable, as event names are populated in actor loop?
            # Also means that event types that have already been added can't be skipped,
            # as there is no way to check -- is this okay to ensure all possible
            # parameters are exported (in case an event is missing one?)?
            json_parent[event_key] = {}
        if not event.data.params:
            continue
        for param in event.data.params.data:
            # Only populate, never overwrite
            # Power users can manually edit the json file (or use the copy parameters button)
            if param not in json_parent[event_key]:
                json_parent[event_key][param] = event.data.params.data[param]
    
    with open(_actor_definitions_path, 'wt') as file:
        json.dump(definitions, file)
