from enum import IntEnum
import typing

from evfl import EventFlow
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

def load_actor_definitions() -> typing.Optional[typing.Dict[str, typing.Any]]:
    try:
        with open(_actor_definitions_path, 'rt') as file:
            return json.loads(file.read())
    except:
        return None

def load_actor_json(actor_name: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not _actor_definitions_path:
        return None

    try:
        # First look for individual actor file (overrides; for power users)
        with open(_actor_definitions_path.parent/f'{actor_name}.json', 'rt') as file:
            return json.load(file)
    except:
        try:
            # Otherwise look in actor definitions file
            with open(_actor_definitions_path, 'rt') as file:
                return json.load(file)[actor_name]
        except:
            return None

def load_event_parameters(actor_name: str, event_name: str, event_type: EventType) -> typing.Optional[typing.Dict[str, typing.Any]]:
    try:
        actor = load_actor_json(actor_name)

        if event_type == EventType.Action:
            return actor['actions'][event_name]
        if event_type == EventType.Query:
            return actor['queries'][event_name]
        return None
    except:
        return None

def load_actions(actor_name: str) -> typing.Optional[typing.Iterable[str]]:
    try:
        return load_actor_json(actor_name)['actions'].keys()
    except:
        return None

def load_queries(actor_name: str) -> typing.Optional[typing.Iterable[str]]:
    try:
        return load_actor_json(actor_name)['queries'].keys()
    except:
        return None

def export_definitions(flow: EventFlow, widget: typing.Optional['QWidget']) -> None:
    if not _actor_definitions_path:
        set_actor_definitions_path(q.QFileDialog.getSaveFileName(widget, 'Export actor definitions to...',  'actor_definitions', 'JSON (*.json)')[0])

    if not _actor_definitions_path:
        return

    definitions = load_actor_definitions() or dict()

    for actor in flow.flowchart.actors:
        actor_root = definitions.get(actor.identifier.name, {})
        definitions[actor.identifier.name] = actor_root

        export_actor_classes(actor_root, 'actions', actor.actions)
        export_actor_classes(actor_root, 'queries', actor.queries)
        #! Potential future addition: support actor parameters + autofill

    for event in flow.flowchart.events:
        if isinstance(event.data, ActionEvent):
            event_root = definitions[event.data.actor.v.identifier.name]['actions']
            event_key = event.data.actor_action.v.v
        elif isinstance(event.data, SwitchEvent):
            event_root = definitions[event.data.actor.v.identifier.name]['queries']
            event_key = event.data.actor_query.v.v
        else:
            # Skip subflows
            continue

        if event_key not in event_root:
            # Shouldn't be reachable, as event names are populated in actor loop?
            # Also means that event types that have already been added can't be skipped,
            # as there is no way to check -- is this okay to ensure all possible
            # parameters are exported (in case an event is missing one?)?
            event_root[event_key] = {}

        if event.data.params:
            for param in event.data.params.data:
                # Only populate, never overwrite
                # Power users can manually edit the json file (or use the copy parameters button)
                if param not in event_root[event_key]:
                    event_root[event_key][param] = event.data.params.data[param]

    with open(_actor_definitions_path, 'wt') as file:
        json.dump(definitions, file)

def export_actor_classes(actor: typing.Dict[str, typing.Any], category: str, classes: typing.List['StringHolder']) -> None:
    category_root = actor.get(category, {})
    actor[category] = category_root

    for c in classes:
        if c.v not in category_root:
            category_root[c.v] = {}
