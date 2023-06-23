from enum import IntEnum
import typing

import json
from pathlib import Path
import PyQt5.QtWidgets as q

_actor_json_path: typing.Optional[Path] = None
def set_actor_json_path(p: typing.Optional[str]) -> None:
    if p:
        global _actor_json_path
        _actor_json_path = Path(p)

class EventType(IntEnum):
    Action = 0
    Query = 1

def load_actor_json(actor_name: str) -> typing.Dict[str, typing.Any]:
    if not _actor_json_path:
        return None

    try:
        # First look for individual actor file (overrides)
        with open(_actor_json_path.parent/f'{actor_name}.json', 'rt') as file:
            return json.loads(file.read())
    except:
        try:
            # Otherwise look in actor definitions file
            with open(_actor_json_path, 'rt') as file:
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

def load_actions(actor_name: str) -> typing.KeysView[str]:
    try:
        return load_actor_json(actor_name)['actions'].keys()
    except:
        return None

def load_queries(actor_name: str) -> typing.KeysView[str]:
    try:
        return load_actor_json(actor_name)['queries'].keys()
    except:
        return None

#! Replace with 'export all actors' menu option
def export_actor_json(actor_name: str, actions: typing.List[str], queries: typing.List[str], widget) -> None:
    if not _actor_json_path:
        set_actor_json_path(q.QFileDialog.getSaveFileName(widget, 'Set ',  'actor_definitions', 'JSON (*.json)')[0])

    if not _actor_json_path:
        return
    
    try:
        with open(_actor_json_path, 'rt') as file:
            definitions = json.loads(file.read())
    except:
        definitions = dict()

    with open(_actor_json_path, 'wt') as file:
        #! Will replace existing entry, user should be prompted
        definitions[actor_name] = {}
        definitions[actor_name]['actions'] = {}
        definitions[actor_name]['queries'] = {}
        #! Also support actor parameters?
        # - currently no auto-complete option at all?

        for action in actions:
            definitions[actor_name]['actions'][action] = {}
            #! Somehow find event and populate with sample parameters
        for query in queries:
            definitions[actor_name]['queries'][query] = {}
            #! Somehow find event and populate with sample parameters

        json.dump(definitions, file)
