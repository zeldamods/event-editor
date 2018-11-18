import typing

import eventeditor.ai as ai
import eventeditor.util as util
from eventeditor.search_bar import SearchBar
from evfl import EventFlow, Actor
from evfl.common import StringHolder
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ActorStringListView(q.QWidget):
    def __init__(self, parent, label_str: str, model, flow_data) -> None:
        super().__init__(parent)
        self.flow_data = flow_data
        self.action_builders = [] # type: ignore
        self.model = model
        self.label_str = label_str

        self.lview = q.QListView()
        self.lview.setModel(self.model)
        self.lview.setContextMenuPolicy(qc.Qt.CustomContextMenu)
        self.lview.customContextMenuRequested.connect(self.onContextMenu)

        self.add_btn = q.QPushButton('Add...')
        self.add_btn.setStyleSheet('padding: 2px 5px;')
        self.add_btn.clicked.connect(self.onAdd)
        box = q.QHBoxLayout()
        label = q.QLabel(label_str)
        label.setStyleSheet('font-weight: bold;')
        box.addWidget(label, stretch=1)
        box.addWidget(self.add_btn)

        layout = q.QVBoxLayout(self)
        layout.addLayout(box)
        layout.addWidget(self.lview, stretch=1)

    def onAdd(self) -> None:
        text = self._getNewString()
        if not text:
            return

        if self.model.has(text):
            q.QMessageBox.critical(self, 'Cannot add', 'This action or query already exists.')
            return

        self.model.append(text)
        self.flow_data.actor_model.refresh()

    def _getNewString(self) -> str:
        text, ok = q.QInputDialog.getText(self, f'{self.label_str}', f'Name of the new action or query:', q.QLineEdit.Normal)
        return text

    def onRemove(self, idx) -> None:
        value = idx.data(qc.Qt.UserRole)
        if util.is_actor_string_in_use(self.flow_data.flow.flowchart.events, value):
            q.QMessageBox.critical(self, 'Cannot remove', 'This action or query cannot be removed because it is in use. Please remove any references to this action or query first.')
            return
        self.model.remove(idx.row())
        self.flow_data.actor_model.refresh()

    def addActionBuilder(self, fn) -> None:
        self.action_builders.append(fn)

    def onContextMenu(self, pos) -> None:
        smodel = self.lview.selectionModel()
        if not smodel.selectedRows():
            return

        idx = smodel.selectedRows()[0]
        menu = q.QMenu()
        menu.addAction('&Remove', lambda: self.onRemove(idx))
        for builder in self.action_builders:
            builder(menu, idx)
        menu.exec_(self.sender().viewport().mapToGlobal(pos))

class ActorAIClassAddDialog(q.QDialog):
    def __init__(self, parent, model) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Add an AI class')
        self.setMinimumWidth(350)

        ledit_hint = q.QLabel('Enter an AI class:')
        ledit_hint.setAlignment(qc.Qt.AlignCenter)
        self._ledit = q.QLineEdit()
        list_hint = q.QLabel('or select one:')
        list_hint.setAlignment(qc.Qt.AlignCenter)

        self._list = q.QListView()
        self._proxy_model = qc.QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(model)
        self._list.setModel(self._proxy_model)
        self._list.setEditTriggers(q.QAbstractItemView.NoEditTriggers)
        self._list.selectionModel().selectionChanged.connect(self._onSelectionChanged)
        self._list.doubleClicked.connect(lambda idx: self.accept())

        self._search_bar = SearchBar()
        self._search_bar.hide()
        self._search_bar.connectToFilterModel(self._proxy_model)
        self._search_bar.addFindShortcut(self)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Ok | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addWidget(ledit_hint)
        layout.addWidget(self._ledit)
        layout.addWidget(list_hint)
        layout.addWidget(self._list)
        layout.addWidget(self._search_bar)
        layout.addWidget(btn_box)

    def accept(self) -> None:
        if not self.getText():
            q.QMessageBox.critical(self, self.windowTitle(), 'Please enter or select an AI class.')
            return
        super().accept()

    def getText(self) -> str:
        return self._ledit.text()

    def _onSelectionChanged(self, selected, deselected) -> None:
        if len(selected.indexes()) <= 0:
            return
        self._ledit.setText(selected.indexes()[0].data(qc.Qt.DisplayRole))

class ActorActionListView(ActorStringListView):
    def __init__(self, parent, model, flow_data) -> None:
        super().__init__(parent, 'Actions', model, flow_data)
        self.actor: typing.Optional[Actor] = None

    def setActor(self, actor: Actor) -> None:
        self.actor = actor

    def _getNewString(self) -> str:
        if not self.actor:
            return ''
        name = self.actor.identifier.name
        aiprog = ai.load_aiprog(name)
        actions = list(aiprog.actions.keys()) if aiprog else []
        add_dialog = ActorAIClassAddDialog(self, qc.QStringListModel(actions, self))
        add_dialog.setWindowTitle(f'Add an action for {name}')
        ret = add_dialog.exec_()
        return add_dialog.getText() if ret else ''

class ActorQueryListView(ActorStringListView):
    def __init__(self, parent, model, flow_data) -> None:
        super().__init__(parent, 'Queries', model, flow_data)
        self.actor: typing.Optional[Actor] = None

    def setActor(self, actor: Actor) -> None:
        self.actor = actor

    def _getNewString(self) -> str:
        if not self.actor:
            return ''
        name = self.actor.identifier.name
        aiprog = ai.load_aiprog(name)
        queries = list(aiprog.queries.keys()) if aiprog else []
        add_dialog = ActorAIClassAddDialog(self, qc.QStringListModel(queries, self))
        add_dialog.setWindowTitle(f'Add a query for {name}')
        ret = add_dialog.exec_()
        return add_dialog.getText() if ret else ''
