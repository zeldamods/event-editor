import json
import typing

from eventeditor.container_model import ContainerModel
from eventeditor.container_view import ContainerView
from eventeditor.event_branch_editors import SwitchEventEditDialog, ForkEventEditDialog
from eventeditor.event_edit_dialog import show_event_editor
from eventeditor.event_chooser_dialog import show_event_type_chooser, add_new_event, EventChooserDialog, CheckableEventParentListWidget
from eventeditor.event_fork_chooser_dialog import EventForkChooserDialog
from eventeditor.flow_data import FlowData
from eventeditor.search_bar import SearchBar
from eventeditor.util import *
from evfl import Container, Flowchart, Actor, Event, EventFlow, ActionEvent, SwitchEvent, ForkEvent, JoinEvent, SubFlowEvent
from evfl.common import Index, RequiredIndex
from evfl.entry_point import EntryPoint
from evfl.enums import EventType
from evfl.util import make_values_to_index_map
from PyQt5.QtWebChannel import QWebChannel # type: ignore
from PyQt5.QtWebEngineWidgets import QWebEngineView # type: ignore
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class GraphBuilder:
    def __init__(self) -> None:
        self.elements: list = []

    def addNode(self, node_id: int, node_type: str, data = dict()) -> int:
        self.elements.append({
            'type': 'node',
            'id': node_id,
            'data': data,
            'node_type': node_type,
        })
        return node_id

    def addEdge(self, source: int, target: int, data = dict()) -> None:
        self.elements.append({
            'type': 'edge',
            'source': source,
            'target': target,
            'data': data,
        })

class FlowchartWebObject(qc.QObject):
    flowDataChanged = qc.pyqtSignal()
    fileLoaded = qc.pyqtSignal(EventFlow)
    eventNameVisibilityChanged = qc.pyqtSignal(bool)
    eventParamVisibilityChanged = qc.pyqtSignal(bool)
    actionProhibitionChanged = qc.pyqtSignal(bool)

    selectRequested = qc.pyqtSignal(int)

    def __init__(self, view) -> None:
        super().__init__(view)
        self.view: FlowchartView = view

    @qc.pyqtSlot(result=qc.QVariant)
    def getJson(self) -> qc.QVariant:
        flow = self.view.flow_data.flow
        if not flow or not flow.flowchart:
            return qc.QVariant(dict())

        actors = flow.flowchart.actors
        events = flow.flowchart.events
        builder = GraphBuilder()
        visited: typing.Set[Event] = set()

        event_idx_map = make_values_to_index_map(events)

        def handleNextEvent(nid, next_event: typing.Optional[Event], join_stack: typing.List[Event]) -> None:
            if not next_event:
                if join_stack:
                    builder.addEdge(nid, event_idx_map[join_stack[-1]], {'virtual': True})
                return
            builder.addEdge(nid, event_idx_map[next_event])
            traverse(next_event, join_stack)

        def traverse(event: Event, join_stack: typing.List[Event]) -> None:
            if event in visited:
                return
            visited.add(event)
            data = event.data

            if isinstance(data, ActionEvent):
                nid = builder.addNode(event_idx_map[event], 'action', {
                    'actor': str(data.actor.v.identifier),
                    'action': str(data.actor_action.v),
                    'name': event.name,
                    'params': data.params.data if data.params else None,
                })
                handleNextEvent(nid, data.nxt.v, join_stack)

            elif isinstance(data, SwitchEvent):
                nid = builder.addNode(event_idx_map[event], 'switch', {
                    'actor': str(data.actor.v.identifier),
                    'query': str(data.actor_query.v),
                    'name': event.name,
                    'params': data.params.data if data.params else None,
                })
                for value, case in data.cases.items():
                    builder.addEdge(nid, event_idx_map[case.v], {'value': value})
                    traverse(case.v, join_stack)
                if join_stack and not (len(data.cases) == 2 and 0 in data.cases and 1 in data.cases):
                    builder.addEdge(nid, event_idx_map[join_stack[-1]], {'virtual': True})

            elif isinstance(data, ForkEvent):
                nid = builder.addNode(event_idx_map[event], 'fork', {'name': event.name})
                join_stack.append(data.join.v)
                for fork in data.forks:
                    builder.addEdge(nid, event_idx_map[fork.v])
                    traverse(fork.v, join_stack)
                traverse(data.join.v, join_stack)

            elif isinstance(data, JoinEvent):
                join_stack.pop()
                nid = builder.addNode(event_idx_map[event], 'join', {'name': event.name})
                handleNextEvent(nid, data.nxt.v, join_stack)

            elif isinstance(data, SubFlowEvent):
                nid = builder.addNode(event_idx_map[event], 'sub_flow', {
                    'res_flowchart_name': data.res_flowchart_name,
                    'entry_point_name': data.entry_point_name,
                    'name': event.name,
                    'params': data.params.data if data.params else None,
                })
                handleNextEvent(nid, data.nxt.v, join_stack)

        for i, entry in enumerate(flow.flowchart.entry_points):
            builder.addNode(-1000-i, 'entry', {'name': entry.name})
            builder.addEdge(-1000-i, event_idx_map[entry.main_event.v])
            traverse(entry.main_event.v, [])

        # Add events that are not linked from any entry point.
        try:
            for event in flow.flowchart.events:
                if event in visited:
                    continue
                traverse(event, [])
        except IndexError as e:
            q.QMessageBox.critical(self.view, 'Bug', f'An error has occurred while generating graph data: {e}\n\nThe graph may be incomplete. Please report this issue and mention what you did before this message showed up.')

        # Manually convert to JSON to ensure custom types are handled in a sane way.
        # (It seems QVariant cannot handle the Argument class and always replaces it with null.)
        return qc.QVariant(json.loads(json.dumps(builder.elements, default=lambda x: str(x))))

    @qc.pyqtSlot()
    def emitReadySignal(self):
        self.view.readySignal.emit()

    @qc.pyqtSlot(int)
    def emitEventSelectedSignal(self, node_id: int) -> None:
        self.view.eventSelected.emit(int(node_id))

    @qc.pyqtSlot()
    def emitReloadedSignal(self):
        self.view.reloadedSignal.emit()

    @qc.pyqtSlot(int)
    def editEvent(self, node_id: int):
        self.view.webEditEvent(int(node_id))

    @qc.pyqtSlot(int)
    def addEntryPoint(self, node_id: int):
        self.view.webAddEntryPoint(int(node_id))

    @qc.pyqtSlot(int)
    def removeEntryPoint(self, node_id: int):
        self.view.webRemoveEntryPoint(-1000-int(node_id))

    @qc.pyqtSlot(list, int)
    def addEventAbove(self, parents: typing.List[int], node_id: int):
        self.view.webAddEventAbove([int(x) for x in parents], int(node_id))

    @qc.pyqtSlot(int)
    def addEventBelow(self, node_id: int):
        self.view.webAddEventBelow(int(node_id))

    @qc.pyqtSlot(int)
    def unlink(self, node_id: int):
        self.view.webUnlink(int(node_id))

    @qc.pyqtSlot(int)
    def link(self, node_id: int):
        self.view.webLink(int(node_id))

    @qc.pyqtSlot(list, int)
    def removeEvent(self, parents: typing.List[int], node_id: int):
        self.view.webRemoveEvent([int(x) for x in parents], int(node_id))

    @qc.pyqtSlot(int)
    def editSwitchBranches(self, node_id: int):
        self.view.webEditSwitchBranches(int(node_id))

    @qc.pyqtSlot(int)
    def editForkBranches(self, node_id: int):
        self.view.webEditForkBranches(int(node_id))

class FlowchartView(q.QWidget):
    selectRequested = qc.pyqtSignal(int)
    eventNameVisibilityChanged = qc.pyqtSignal(bool)
    eventParamVisibilityChanged = qc.pyqtSignal(bool)

    # View -> Core
    readySignal = qc.pyqtSignal()
    reloadedSignal = qc.pyqtSignal()
    eventSelected = qc.pyqtSignal(int)

    def __init__(self, parent, flow_data: FlowData) -> None:
        super().__init__(parent)
        self.flow_data: FlowData = flow_data
        self.is_current = True
        self.selected_event: typing.Optional[Event] = None
        self.initWidgets()
        self.initLayout()
        self.connectWidgets()

    def initWidgets(self) -> None:
        self.web_object = FlowchartWebObject(self)
        self.flow_data.flowDataChanged.connect(self.onFlowDataChanged)
        self.flow_data.fileLoaded.connect(self.web_object.fileLoaded)
        self.selectRequested.connect(self.web_object.selectRequested)
        self.eventNameVisibilityChanged.connect(self.web_object.eventNameVisibilityChanged)
        self.eventParamVisibilityChanged.connect(self.web_object.eventParamVisibilityChanged)

        self.view = QWebEngineView()
        self.view.setContextMenuPolicy(qc.Qt.NoContextMenu)
        self.channel = QWebChannel()
        self.channel.registerObject('widget', self.web_object)
        self.view.page().setWebChannel(self.channel)
        self.view.page().setBackgroundColor(qg.QColor(0x38, 0x38, 0x38));
        self.view.setUrl(qc.QUrl.fromLocalFile(get_path('assets/index.html')))

        self.entry_point_view = q.QListView(self)
        self.ep_proxy_model = qc.QSortFilterProxyModel(self)
        self.ep_proxy_model.setSourceModel(self.flow_data.entry_point_model)
        self.ep_proxy_model.setFilterKeyColumn(-1)
        self.entry_point_view.setModel(self.ep_proxy_model)
        self.ep_search = SearchBar()
        self.ep_search.hide()

        self.container_model = ContainerModel(self)
        self.container_view = ContainerView(None, self.container_model, self.flow_data)
        self.container_stacked_widget = q.QStackedWidget()
        self.container_stacked_widget.addWidget(q.QWidget())
        self.container_stacked_widget.addWidget(self.container_view)

        self.update_timer = qc.QTimer(self)
        self.update_timer.timeout.connect(self.web_object.flowDataChanged)
        self.update_timer.setSingleShot(True)

    def initLayout(self) -> None:
        left_pane_splitter = q.QSplitter(qc.Qt.Vertical)
        ep_widget = q.QWidget()
        ep_layout = q.QVBoxLayout(ep_widget)
        ep_layout.setContentsMargins(0, 0, 0, 0)
        ep_layout.addWidget(self.entry_point_view, stretch=1)
        ep_layout.addWidget(self.ep_search)
        left_pane_splitter.addWidget(ep_widget)
        left_pane_splitter.addWidget(self.container_stacked_widget)
        left_pane_splitter.setSizes([left_pane_splitter.height() * 0.6, left_pane_splitter.height() * 0.4])

        splitter = q.QSplitter()
        splitter.addWidget(left_pane_splitter)
        splitter.addWidget(self.view)
        splitter.setSizes([splitter.width() * 0.3, splitter.width() * 0.7])
        layout = q.QHBoxLayout(self)
        layout.addWidget(splitter)
        layout.setContentsMargins(0, 0, 0, 0)

    def connectWidgets(self) -> None:
        self.ep_search.connectToFilterModel(self.ep_proxy_model)
        find_action = q.QAction(self)
        find_action.setShortcut(qg.QKeySequence.Find)
        find_action.triggered.connect(self.ep_search.showAndFocus)
        self.addAction(find_action)

        self.flow_data.flowDataChanged.connect(self.entry_point_view.clearSelection)
        self.entry_point_view.selectionModel().selectionChanged.connect(self.onEntryPointSelected)

        connect_model_change_signals(self.container_model, self.flow_data, reload_flowchart_needed=False)
        self.eventSelected.connect(self.onEventSelectedInWebView)
        self.flow_data.flowDataChanged.connect(self.refreshParamModel)

        self.reloadedSignal.connect(self.onWebViewReloaded)

    def setIsCurrentView(self, is_current: bool) -> None:
        self.is_current = is_current
        if is_current and self.update_timer.isActive():
            self.update_timer.stop()
            self.web_object.flowDataChanged.emit()

    def reload(self) -> None:
        self.view.reload()

    def onWebViewReloaded(self) -> None:
        if not self.selected_event or not self.flow_data.flow or not self.flow_data.flow.flowchart:
            return

        try:
            new_idx = self.flow_data.flow.flowchart.events.index(self.selected_event)
            self.selectRequested.emit(new_idx)
        except ValueError:
            self.container_model.set(None)
            self.container_stacked_widget.setCurrentIndex(0)

    def refreshParamModel(self) -> bool:
        if self.selected_event and hasattr(self.selected_event.data, 'params'):
            if not self.selected_event.data.params: # type: ignore
                self.selected_event.data.params = Container() # type: ignore
            self.container_model.set(self.selected_event.data.params) # type: ignore
            self.container_stacked_widget.setCurrentIndex(1)
            return True
        return False

    def onEventSelectedInWebView(self, idx: int) -> None:
        if idx >= 0:
            event = self.flow_data.flow.flowchart.events[idx]
            self.selected_event = event
            if self.refreshParamModel():
                return
        else:
            self.selected_event = None

        self.container_model.set(None)
        self.container_stacked_widget.setCurrentIndex(0)

    def onFlowDataChanged(self) -> None:
        if not self.flow_data.reload_flowchart_needed:
            return
        if self.is_current:
            self.web_object.flowDataChanged.emit()
        else:
            self.update_timer.start(15*1000)

    def onEntryPointSelected(self, selected, deselected) -> None:
        if len(selected.indexes()) != 1:
            return
        idx = selected.indexes()[0]
        self.selectRequested.emit(-1000-self.ep_proxy_model.mapToSource(idx).row())

    def delayedSelect(self, event: Event) -> None:
        try:
            qc.QTimer.singleShot(1000, lambda:
                self.selectRequested.emit(self.flow_data.flow.flowchart.events.index(event)))
        except ValueError:
            pass

    def webEditEvent(self, idx: int) -> None:
        if idx < 0:
            return
        show_event_editor(self, self.flow_data, idx)

    def webAddEntryPoint(self, event_idx: int) -> None:
        if event_idx < 0:
            return

        ep_name, ok = q.QInputDialog.getText(self, 'Add entry point', f'Name of the new entry point:', q.QLineEdit.Normal)
        if not ok or not ep_name:
            return

        ep = EntryPoint(ep_name)
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        ep.main_event.v = self.flow_data.flow.flowchart.events[event_idx]
        self.flow_data.entry_point_model.append(ep)

    def webRemoveEntryPoint(self, ep_idx: int) -> None:
        try:
            self.flow_data.entry_point_model.removeRow(ep_idx)
        except IndexError as e:
            q.QMessageBox.critical(self, 'Bug', f'An error has occurred: {e}\n\nPlease report this issue and mention what you were doing when this message showed up.')

    def addNewEvent(self) -> typing.Optional[Event]:
        return add_new_event(self, self.flow_data)

    def webAddEventAbove(self, parent_indices: typing.List[int], event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]

        parent_events = [self.flow_data.flow.flowchart.events[i] for i in parent_indices if i >= 0]
        list_widget = CheckableEventParentListWidget(None, event, parent_events)
        if parent_events:
            dialog = q.QDialog(self, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
            dialog.setWindowTitle('Add new event above...')
            btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Ok | q.QDialogButtonBox.Cancel);
            btn_box.accepted.connect(dialog.accept)
            btn_box.rejected.connect(dialog.reject)
            dialog_layout = q.QVBoxLayout(dialog)
            dialog_layout.addWidget(q.QLabel('Please select links that should be modified to point to the new event you are going to add.'))
            dialog_layout.addWidget(list_widget)
            dialog_layout.addWidget(btn_box)
            ret = dialog.exec_()
            if not ret:
                return

        new_parent = self.addNewEvent()
        if not new_parent:
            return

        self._doAddEventAbove(list_widget.getSelectedEvents(), event, new_parent)
        self.flow_data.flowDataChanged.emit()
        self.delayedSelect(new_parent)

    def _doAddEventAbove(self, parents: typing.List[typing.Tuple[Event, typing.List[typing.Any]]], event: Event, new_parent: Event) -> None:
        # Update the parents to point to the new parent.
        for parent, branches in parents:
            if isinstance(parent.data, ActionEvent) or isinstance(parent.data, JoinEvent) or isinstance(parent.data, SubFlowEvent):
                # Easy case: just set the next pointer to the new parent.
                parent.data.nxt.v = new_parent

            # For switch and fork events, update all branches that currently point to the event.
            elif isinstance(parent.data, SwitchEvent):
                for case in branches:
                    if parent.data.cases[case].v == event:
                        parent.data.cases[case].v = new_parent
            elif isinstance(parent.data, ForkEvent):
                for i, fork in enumerate(branches):
                    if fork.v == event:
                        parent.data.forks[i].v = new_parent

        # Make the new parent point to the event.
        if isinstance(new_parent.data, ActionEvent):
            new_parent.data.nxt.v = event
        elif isinstance(new_parent.data, SwitchEvent):
            new_parent.data.cases[-1] = RequiredIndex()
            new_parent.data.cases[-1].v = event
        elif isinstance(new_parent.data, SubFlowEvent):
            new_parent.data.nxt.v = event
        elif isinstance(new_parent.data, ForkEvent):
            new_parent.data.forks.clear()
            ri: RequiredIndex[Event] = RequiredIndex()
            ri.v = event
            new_parent.data.forks.append(ri)

    def webAddEventBelow(self, event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]
        new_event = self.addNewEvent()
        if new_event:
            self.webDoAddEventBelow(event, new_event)

    def webDoAddEventBelow(self, event: Event, target: Event) -> None:
        if not (isinstance(event.data, ActionEvent) or isinstance(event.data, SubFlowEvent) or isinstance(event.data, JoinEvent)):
            return

        if isinstance(target.data, ActionEvent):
            target.data.nxt.v = event.data.nxt.v
        elif isinstance(target.data, SwitchEvent):
            if event.data.nxt.v:
                target.data.cases[-1] = RequiredIndex()
                target.data.cases[-1].v = event.data.nxt.v
        elif isinstance(target.data, SubFlowEvent):
            target.data.nxt.v = event.data.nxt.v

        event.data.nxt.v = target

        self.flow_data.flowDataChanged.emit()
        self.delayedSelect(target)

    def webLink(self, event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]
        self.web_object.actionProhibitionChanged.emit(True)
        dialog = EventChooserDialog(self, self.flow_data)
        dialog.event_view.jumpToFlowchartRequested.connect(self.selectRequested)
        self.eventSelected.connect(dialog.event_view.selectEvent)
        dialog.accepted.connect(lambda: self.webDoLink(event, dialog.getSelectedEvent()))
        dialog.finished.connect(lambda: self.web_object.actionProhibitionChanged.emit(False))
        dialog.show()

    def webDoLink(self, event: Event, target: Event) -> None:
        if event == target:
            q.QMessageBox.critical(self, 'Invalid choice', 'Cannot link an event to itself. Please choose another event and try again.')
            return
        event.data.nxt.v = target # type: ignore
        self.flow_data.flowDataChanged.emit()
        self.delayedSelect(target)

    def webUnlink(self, event_idx: int) -> None:
        ret = q.QMessageBox.question(self, 'Unlink', 'Warning: Unlinking events that are in nested fork branches can currently result in graph corruption. Continue?')
        if ret != q.QMessageBox.Yes:
            return

        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]
        event.data.nxt.v = None # type: ignore
        self.flow_data.flowDataChanged.emit()
        self.delayedSelect(event)

    def _findForkEventLeafNodes(self, starting_event: Event) -> typing.List[Event]:
        assert isinstance(starting_event.data, ForkEvent)
        parents: typing.List[Event] = []
        visited: typing.Set[Event] = set()

        def handleNextEvent(event: Event, next_event: typing.Optional[Event], join_stack: typing.List[Event]) -> None:
            if not next_event:
                if not join_stack:
                    parents.append(event)
                return
            traverse(next_event, join_stack)

        def traverse(event: Event, join_stack: typing.List[Event]) -> None:
            if event in visited:
                return
            visited.add(event)
            data = event.data
            if isinstance(data, ActionEvent):
                handleNextEvent(event, data.nxt.v, join_stack)
            elif isinstance(data, SwitchEvent):
                for value, case in data.cases.items():
                    traverse(case.v, join_stack)
            elif isinstance(data, ForkEvent):
                join_stack.append(data.join.v)
                for fork in data.forks:
                    traverse(fork.v, join_stack)
                traverse(data.join.v, join_stack)
            elif isinstance(data, JoinEvent):
                join_stack.pop()
                handleNextEvent(event, data.nxt.v, join_stack)
            elif isinstance(data, SubFlowEvent):
                handleNextEvent(event, data.nxt.v, join_stack)

        for fork in starting_event.data.forks:
            traverse(fork.v, [])
        return parents

    def _doRemoveEvent(self, parents: typing.List[Event], event_idx: int) -> None:
        """Erase an event from the tree, ensuring that the next pointers of parents are updated.

        This does not resize the event list. None items must be removed from the list afterwards."""
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]

        next_event: typing.Optional[Event] = None
        if isinstance(event.data, ActionEvent) or isinstance(event.data, JoinEvent) or isinstance(event.data, SubFlowEvent):
            next_event = event.data.nxt.v
        elif isinstance(event.data, SwitchEvent):
            next_event = next(iter(event.data.cases.values())).v if event.data.cases else None
        elif isinstance(event.data, ForkEvent):
            assert len(event.data.forks) == 1
            next_event = event.data.forks[0].v

        # Don't let the user delete the only branch in a fork event
        if len(parents) == 1 and isinstance(parents[0].data, ForkEvent) and len(parents[0].data.forks) == 1 and not next_event:
            q.QMessageBox.information(self, 'Cannot remove', 'Please delete the parent fork event first.')
            return

        # Make the parents point to the next event.
        for parent in parents:
            if isinstance(parent.data, ActionEvent) or isinstance(parent.data, JoinEvent) or isinstance(parent.data, SubFlowEvent):
                parent.data.nxt.v = next_event

            # For switch and fork events, update all branches that currently point to the event.
            # Or remove them if there is no next event.
            elif isinstance(parent.data, SwitchEvent):
                for case in list(parent.data.cases.keys()):
                    if parent.data.cases[case].v == event:
                        if next_event:
                            parent.data.cases[case].v = next_event
                        else:
                            del parent.data.cases[case]
            elif isinstance(parent.data, ForkEvent):
                new_forks = []
                for fork in parent.data.forks:
                    if fork.v != event:
                        new_forks.append(fork)
                    elif next_event:
                        ri: RequiredIndex[Event] = RequiredIndex()
                        ri.v = next_event
                        new_forks.append(ri)
                parent.data.forks = new_forks

        # If we are removing a fork event, also remove the associated join.
        if isinstance(event.data, ForkEvent):
            self._doRemoveEvent(self._findForkEventLeafNodes(event),
                self.flow_data.flow.flowchart.events.index(event.data.join.v))

        # Ensure that entry points point to the correct event.
        for entry_point in self.flow_data.flow.flowchart.entry_points:
            if entry_point.main_event.v == event:
                entry_point.main_event.v = next_event

        # Erase this event from the list. None elements will be swept by the caller.
        self.flow_data.flow.flowchart.events[event_idx] = None # type: ignore

    def webRemoveEvent(self, parent_indices: typing.List[int], event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart

        parents = [self.flow_data.flow.flowchart.events[idx] for idx in parent_indices if idx >= 0]
        self._doRemoveEvent(parents, event_idx)
        self.flow_data.flow.flowchart.events = \
            [event for event in self.flow_data.flow.flowchart.events if event is not None]
        # Since we're editing the array directly, a model reset MUST be triggered.
        self.flow_data.event_model.set(self.flow_data.flow)

        self.flow_data.flowDataChanged.emit()

    def webEditSwitchBranches(self, event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]
        if not isinstance(event.data, SwitchEvent):
            return
        self.web_object.actionProhibitionChanged.emit(True)
        dialog = SwitchEventEditDialog(self, event.data.cases, self.flow_data)
        dialog.finished.connect(lambda: self.web_object.actionProhibitionChanged.emit(False))
        dialog.chooserEventDoubleClicked.connect(self.selectRequested)
        self.eventSelected.connect(dialog.chooserSelectSignal)
        dialog.show()

    def webEditForkBranches(self, event_idx: int) -> None:
        if event_idx < 0:
            return
        assert self.flow_data.flow and self.flow_data.flow.flowchart
        event = self.flow_data.flow.flowchart.events[event_idx]
        if not isinstance(event.data, ForkEvent):
            return
        self.web_object.actionProhibitionChanged.emit(True)
        dialog = ForkEventEditDialog(self, event.data.forks, self.flow_data)
        dialog.finished.connect(lambda: self.web_object.actionProhibitionChanged.emit(False))
        dialog.chooserEventDoubleClicked.connect(self.selectRequested)
        self.eventSelected.connect(dialog.chooserSelectSignal)
        dialog.show()

    def addFork(self) -> None:
        self.web_object.actionProhibitionChanged.emit(True)
        dialog = EventForkChooserDialog(self, self.flow_data)
        dialog.finished.connect(lambda: self.web_object.actionProhibitionChanged.emit(False))
        dialog.accepted.connect(lambda: self._doAddFork(*dialog.getEventPair()))
        dialog.chooserEventDoubleClicked.connect(self.selectRequested)
        self.eventSelected.connect(dialog.chooserSelectSignal)
        dialog.show()

    def _findEventParentNodes(self, event: Event) -> typing.List[typing.Tuple[Event, typing.List[typing.Any]]]:
        parents: typing.List[typing.Tuple[Event, typing.List[typing.Any]]] = []
        for e in self.flow_data.flow.flowchart.events:
            data = e.data
            if isinstance(data, ActionEvent) or isinstance(data, JoinEvent) or isinstance(data, SubFlowEvent):
                if data.nxt.v == event:
                    parents.append((e, []))
            elif isinstance(data, SwitchEvent):
                if any(case.v == event for case in data.cases.values()):
                    parents.append((e, list(data.cases.keys())))
            elif isinstance(data, ForkEvent):
                if any(fork.v == event for fork in data.forks):
                    parents.append((e, data.forks))
        return parents

    def _doAddFork(self, start: Event, end: Event) -> None:
        if not (isinstance(end.data, ActionEvent) or isinstance(end.data, SubFlowEvent)):
            q.QMessageBox.critical(self, 'Not implemented', 'The end event must be an action or sub flow event currently')
            return

        assert self.flow_data.flow and self.flow_data.flow.flowchart

        # Add the fork event as a parent.
        fork_event = Event()
        fork_event.name = self.flow_data.generateEventName()
        fork_event.data = ForkEvent()
        # Add the event manually and do NOT send change signals until the join event is added.
        self.flow_data.flow.flowchart.events.append(fork_event)
        self._doAddEventAbove(self._findEventParentNodes(start), start, fork_event)

        # Fix entry points.
        for entry_point in self.flow_data.flow.flowchart.entry_points:
            if entry_point.main_event.v == start:
                entry_point.main_event.v = fork_event

        # Add the join event as a child.
        join_event = Event()
        join_event.name = self.flow_data.generateEventName()
        join_event.data = JoinEvent()
        join_event.data.nxt.v = end.data.nxt.v
        end.data.nxt.v = None
        self.flow_data.flow.flowchart.events.append(join_event)
        fork_event.data.join.v = join_event

        # Trigger a full model reset since we updated the underlying array directly.
        self.flow_data.event_model.set(self.flow_data.flow)
        self.flow_data.flowDataChanged.emit()
