import typing

import eventeditor.actor_json as aj
from evfl import EventFlow
from evfl.event import ActionEvent, SwitchEvent

def reorder_event_flow_parameters(flow: EventFlow) -> None:
    # Should probably cache definition loads, though
    # current is useful for ensuring latest file version
    for event in flow.flowchart.events:
        if isinstance(event.data, ActionEvent):
            definition = aj.load_event_parameters(event.data.actor.v.identifier.name, event.data.actor_action.v.v, aj.EventType.Action)
        elif isinstance(event.data, SwitchEvent):
            definition = aj.load_event_parameters(event.data.actor.v.identifier.name, event.data.actor_query.v.v, aj.EventType.Query)
        else:
            continue

        # Nothing to sort
        if not event.data.params:
            continue

        # No defined order to sort by
        if not definition:
            continue

        reorder_event_parameters(event.data.params.data, definition)

# Parameters not contained in the definition will be left at the start of the collection
def reorder_event_parameters(params: typing.Dict[str, typing.Any], definition: typing.Iterable[str]) -> None:
    for param in definition:
        if param in params:
            params[param] = params.pop(param)
