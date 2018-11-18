from enum import IntEnum, auto
import typing

from eventeditor.event_edit_dialog import show_event_editor
from eventeditor.event_model import EventModelColumn
from eventeditor.search_bar import SearchBar
from evfl import Event, EventFlow
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class _TableWidget(q.QTableView):
    onEnterPressed = qc.pyqtSignal()
    def keyPressEvent(self, event):
        key = event.key()
        if key == qc.Qt.Key_Return or key == qc.Qt.Key_Enter:
            self.onEnterPressed.emit()
        else:
            super().keyPressEvent(event)

class EventView(q.QWidget):
    jumpToFlowchartRequested = qc.pyqtSignal(int)

    def __init__(self, parent, flow_data, enable_ctx_menu: bool=True) -> None:
        super().__init__(parent)
        self.flow_data = flow_data
        self.enable_ctx_menu = enable_ctx_menu
        self.initWidgets()
        self.initLayout()
        self.connectWidgets()

    def initWidgets(self) -> None:
        self.event_proxy_model = qc.QSortFilterProxyModel(self)
        self.event_proxy_model.setSourceModel(self.flow_data.event_model)
        self.event_view = _TableWidget()
        self.event_view.setModel(self.event_proxy_model)
        self.event_view.verticalHeader().hide()
        self.event_view.setSelectionBehavior(q.QAbstractItemView.SelectRows)
        self.event_view.setSelectionMode(q.QAbstractItemView.SingleSelection)
        self.event_view.horizontalHeader().setMinimumSectionSize(80)
        self.event_view.horizontalHeader().setSectionResizeMode(q.QHeaderView.ResizeToContents)
        self.event_view.horizontalHeader().setSectionResizeMode(0, q.QHeaderView.ResizeToContents)
        self.event_view.horizontalHeader().setSectionResizeMode(2, q.QHeaderView.Stretch)
        self.event_view.horizontalHeader().setSectionResizeMode(3, q.QHeaderView.ResizeToContents)
        self.event_view.horizontalHeader().setSectionResizeMode(4, q.QHeaderView.Stretch)

        if self.enable_ctx_menu:
            self.event_view.setContextMenuPolicy(qc.Qt.CustomContextMenu)
            self.event_view.customContextMenuRequested.connect(self.onContextMenu)

        self.search_bar = SearchBar()

    def initLayout(self) -> None:
        layout = q.QVBoxLayout(self)
        layout.addWidget(self.event_view)
        layout.addWidget(self.search_bar)
        self.search_bar.hide()
        layout.setContentsMargins(0, 0, 0, 0)

    def connectWidgets(self) -> None:
        self.event_proxy_model.setFilterKeyColumn(-1)
        self.search_bar.connectToFilterModel(self.event_proxy_model)
        self.search_bar.addFindShortcut(self)

        self.event_view.onEnterPressed.connect(self.onEnterPressed)
        self.event_view.doubleClicked.connect(lambda idx: self.jumpToFlowchartRequested.emit(self.event_proxy_model.mapToSource(idx).row()))

    def getSelectedEventIdx(self) -> typing.Optional[qc.QModelIndex]:
        smodel = self.event_view.selectionModel()
        if not smodel.hasSelection():
            return None
        return self.event_proxy_model.mapToSource(smodel.selectedRows()[0])

    def getSelectedEvent(self) -> typing.Optional[Event]:
        source_idx = self.getSelectedEventIdx()
        if not source_idx:
            return None
        return source_idx.data(qc.Qt.UserRole)

    def selectEvent(self, event_idx: int) -> None:
        model = self.flow_data.event_model
        mapped_idx = self.event_proxy_model.mapFromSource(model.createIndex(event_idx, 0))
        if mapped_idx.isValid():
            self.event_view.selectRow(mapped_idx.row())

    def editEvent(self, event_idx: int) -> None:
        show_event_editor(self, self.flow_data, event_idx)

    def onContextMenu(self, pos) -> None:
        smodel = self.event_view.selectionModel()
        if not smodel.hasSelection():
            return

        sidx = smodel.selectedRows()[0]
        source_idx = self.event_proxy_model.mapToSource(sidx)
        menu = q.QMenu()
        menu.addAction('&Edit...', lambda: self.editEvent(source_idx.row()))
        menu.addAction('&Jump to flowchart', lambda: self.jumpToFlowchartRequested.emit(source_idx.row()))
        menu.exec_(self.sender().viewport().mapToGlobal(pos))

    def onEnterPressed(self) -> None:
        selected_idx = self.getSelectedEventIdx()
        if selected_idx:
            self.jumpToFlowchartRequested.emit(selected_idx.row())
