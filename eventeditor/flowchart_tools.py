import json
import typing

from evfl import EventFlow
from evfl.event import ActionEvent, SwitchEvent

def reorder_event_flow_parameters(flow: EventFlow, definitions: typing.Dict[str, typing.Any]) -> None:
    for event in flow.flowchart.events:
        if isinstance(event.data, ActionEvent):
            definition = definitions[event.data.actor.v.identifier.name]['actions'][event.data.actor_action.v.v].keys()
        elif isinstance(event.data, SwitchEvent):
            definition = definitions[event.data.actor.v.identifier.name]['queries'][event.data.actor_query.v.v].keys()
        else:
            continue

        if not definition:
            if isinstance(event.data, ActionEvent):
                event_type = event.data.actor_action.v.v
            elif isinstance(event.data, SwitchEvent):
                event_type = event.data.actor_query.v.v
            print(f' > {event.data.actor.v.identifier.name}::{event.name} ({event_type})')
            continue

        reorder_event_parameters(event.data.params.data, definition)

# Parameters not contained in the definition will be left at the start of the collection
def reorder_event_parameters(params: typing.Dict[str, typing.Any], definition: typing.Iterable[str]) -> None:
    for param in definition:
        if param in params:
            params[param] = params.pop(param)
