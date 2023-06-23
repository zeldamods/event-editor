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
        # Try loading from a single file with all actors first
        # before looking for individual actor files?
        with open(_actor_json_path/f'{actor_name}.json', 'rt') as stream:
            return json.loads(stream.read())
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

def export_actor_json(actor_name: str, actions: typing.List[str], queries: typing.List[str], window) -> None:
    # Should open existing file and insert/replace actor entry?

    data = dict()
    data['actions'] = {}
    data['queries'] = {}
    # Also support actor parameters?

    for action in actions:
        data['actions'][action] = {}
    for query in queries:
        data['queries'][query] = {}

    filename = str(_actor_json_path/f'{actor_name}') if _actor_json_path else actor_name
    path = q.QFileDialog.getSaveFileName(window, 'Export as...',  filename, 'JSON (*.json)')[0]

    if not path:
        return

    with open(path, 'wt') as file:
        json.dump(data, file)
    file.close()
