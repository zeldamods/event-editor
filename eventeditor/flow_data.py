import enum
from eventeditor.actor_model import ActorModel
from eventeditor.autosave import AutoSaveSystem
from eventeditor.entry_point_model import EntryPointModel
from eventeditor.event_model import EventModel
import eventeditor.util as util
from evfl import EventFlow
import PyQt5.QtCore as qc # type: ignore
import re
import typing

class FlowDataChangeReason(enum.Flag):
    Unknown = enum.auto()
    Reset = enum.auto()
    Actors = enum.auto()
    Events = enum.auto()
    EventParameters = enum.auto()
    EventFlowRename = enum.auto()

class FlowData(qc.QObject):
    flowDataChanged = qc.pyqtSignal(FlowDataChangeReason)
    fileLoaded = qc.pyqtSignal(EventFlow)

    def __init__(self) -> None:
        super().__init__()

        self.auto_save = AutoSaveSystem()
        self.fileLoaded.connect(lambda: self.auto_save.reset())
        self.flowDataChanged.connect(lambda reason: self.auto_save.save(self.flow))

        self.flow: typing.Optional[EventFlow] = None

        self.actor_model = ActorModel()
        self.entry_point_model = EntryPointModel()
        self.event_model = EventModel()

        util.connect_model_change_signals(self.actor_model, self, FlowDataChangeReason.Actors)
        util.connect_model_change_signals(self.entry_point_model, self, FlowDataChangeReason.Events)
        util.connect_model_change_signals(self.event_model, self, FlowDataChangeReason.Events)

        self._next_event_idx = 0

    def setFlow(self, flow: typing.Optional[EventFlow]) -> None:
        self.flow = flow
        self.actor_model.set(flow)
        self.entry_point_model.set(flow)
        self.event_model.set(flow)
        self.flowDataChanged.emit(FlowDataChangeReason.Reset)
        self.fileLoaded.emit(flow)

        self._next_event_idx = self.computeNextEventIdx()

    def computeNextEventIdx(self) -> int:
        if not self.flow or not self.flow.flowchart:
            return -1
        pattern = re.compile(r'^Event(\d+)$')
        max_id = 0
        for event in self.flow.flowchart.events:
            match = pattern.match(event.name)
            if match:
                max_id = max(max_id, int(match[1]))
        return max_id + 1

    def generateEventName(self) -> str:
        name = f'Event{self._next_event_idx}'
        self._next_event_idx += 1
        return name
