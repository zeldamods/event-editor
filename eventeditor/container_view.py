from enum import IntEnum, auto
import typing
import yaml

from eventeditor.container_model import ContainerModel, ContainerModelColumn
from eventeditor.data_editors import CustomTableView
import eventeditor.util as util
from evfl import ActorIdentifier, Argument, Container
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ContainerAddItemDialogType(IntEnum):
    Value = 0
    ActorIdentifier = auto()
    Argument = auto()

class ContainerAddItemDialog(q.QDialog):
    def __init__(self, parent, model: ContainerModel) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle(f'Add container item')
        self.resize(500, 100)
        self.model = model

        self.key_ledit = q.QLineEdit()
        self.createTypeWidgets()
        self.createValueWidgets()

        form_layout = q.QFormLayout()
        form_layout.addRow('&Key:', self.key_ledit)
        form_layout.addRow('Type:', self.type_layout)
        form_layout.addRow('&Value:', self.value_widget)

        layout = q.QVBoxLayout(self)
        layout.addLayout(form_layout)
        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def createTypeWidgets(self) -> None:
        self.type_group = q.QButtonGroup()
        self.type_layout = q.QHBoxLayout()
        def add_type_choice(label_text, btn_id):
            rbtn = q.QRadioButton(label_text)
            self.type_group.addButton(rbtn, btn_id)
            self.type_layout.addWidget(rbtn)
        add_type_choice('&Int/float/bool/string/array', ContainerAddItemDialogType.Value)
        add_type_choice('&Actor identifier', ContainerAddItemDialogType.ActorIdentifier)
        add_type_choice('Ar&gument', ContainerAddItemDialogType.Argument)
        self.type_group.button(ContainerAddItemDialogType.Value).setChecked(True)
        self.type_layout.addStretch()
        self.type_group.buttonClicked[int].connect(self.onTypeBtnClicked)

    def createValueWidgets(self) -> None:
        self.value_widget = q.QStackedWidget()

        self.tedit = q.QPlainTextEdit()
        font = qg.QFontDatabase.systemFont(qg.QFontDatabase.FixedFont)
        font.setPointSize(font.pointSize() * 1.05)
        self.tedit.setFont(font)
        self.tedit.setPlaceholderText('Item data (YAML)\nExamples:\n[1, 2, 3]\n3.1415\ntrue')
        self.value_widget.addWidget(self.tedit)

        actor_id_widget = q.QWidget()
        actor_id_form = q.QFormLayout(actor_id_widget)
        self.actor_id_name_box = q.QLineEdit()
        actor_id_form.addRow('&Name:', self.actor_id_name_box)
        self.actor_id_sub_name_box = q.QLineEdit()
        actor_id_form.addRow('&Sub name:', self.actor_id_sub_name_box)
        self.value_widget.addWidget(actor_id_widget)

        argument_widget = q.QWidget()
        argument_layout = q.QVBoxLayout(argument_widget)
        self.argument_box = q.QLineEdit()
        argument_layout.addWidget(self.argument_box)
        argument_layout.addStretch()
        self.value_widget.addWidget(argument_widget)

    def onTypeBtnClicked(self, btn_id: int) -> None:
        self.value_widget.setCurrentIndex(btn_id)

    def parseValue(self) -> typing.Any:
        try:
            data = yaml.load(self.tedit.toPlainText(), Loader=yaml.SafeLoader)
        except yaml.parser.ParserError as e:
            q.QMessageBox.critical(self, 'Invalid data', f'Could not parse item data. Please verify that the syntax is correct and try again.\n\nDetails:\n\n{e}')
            return None

        if isinstance(data, list):
            if not data:
                q.QMessageBox.critical(self, 'Invalid data', 'Arrays must contain at least one element.')
                return None
            if not util.is_valid_container_value_type(data[0]):
                q.QMessageBox.critical(self, 'Invalid data', f'{type(data[0]).__name__} is not a valid data type.')
                return None
            if not util.is_list_homogeneous(data):
                q.QMessageBox.critical(self, 'Invalid data', 'Arrays can only contain one element type.')
                return None
        else:
            if not util.is_valid_container_value_type(data):
                q.QMessageBox.critical(self, 'Invalid data', f'{type(data).__name__} is not a valid data type.')
                return None

        return data

    def parseActorIdentifier(self) -> typing.Any:
        identifier = ActorIdentifier(self.actor_id_name_box.text(), self.actor_id_sub_name_box.text())
        if not identifier.name:
            q.QMessageBox.critical(self, 'Invalid actor identifier', 'The actor name cannot be empty.')
            return None
        return identifier

    def parseArgument(self) -> typing.Any:
        argument = Argument(self.argument_box.text())
        if not argument:
            q.QMessageBox.critical(self, 'Invalid argument', 'The argument name cannot be empty.')
            return None
        return argument

    def accept(self) -> None:
        key_name: str = self.key_ledit.text()
        if not key_name:
            q.QMessageBox.critical(self, 'Invalid key', 'The key name cannot be empty.')
            return
        if self.model.has(key_name):
            q.QMessageBox.critical(self, 'Invalid key', f'{key_name} is already used.')
            return

        type_id = self.type_group.checkedId()
        data = None
        if type_id == ContainerAddItemDialogType.Value:
            data = self.parseValue()
        elif type_id == ContainerAddItemDialogType.ActorIdentifier:
            data = self.parseActorIdentifier()
        elif type_id == ContainerAddItemDialogType.Argument:
            data = self.parseArgument()

        if data is None:
            return

        self.model.insertItem(key_name, data)
        super().accept()

class ContainerView(q.QWidget):
    autofillRequested = qc.pyqtSignal()

    def __init__(self, parent, model: ContainerModel, flow_data, has_autofill_btn=False) -> None:
        super().__init__(parent)
        self.flow_data = flow_data
        self.action_builders = [] # type: ignore
        self.model: ContainerModel = model

        self.tview = CustomTableView()
        font = qg.QFont()
        font.setPointSize(max(int(font.pointSize() * 0.85), 9))
        self.tview.setFont(font)
        self.tview.setModel(self.model)
        self.tview.verticalHeader().hide()
        self.tview.verticalHeader().setSectionResizeMode(q.QHeaderView.ResizeToContents)
        self.tview.setSelectionMode(q.QAbstractItemView.SingleSelection)
        hheader = self.tview.horizontalHeader()
        hheader.setSectionResizeMode(q.QHeaderView.ResizeToContents)
        hheader.setSectionResizeMode(ContainerModelColumn.Value, q.QHeaderView.Stretch)
        hheader.setMinimumSectionSize(50)
        self.tview.setContextMenuPolicy(qc.Qt.CustomContextMenu)
        self.tview.customContextMenuRequested.connect(self.onContextMenu)
        util.set_view_delegate(self.tview)

        self.add_btn = q.QPushButton('Add...')
        self.add_btn.setStyleSheet('padding: 2px 5px;')
        self.add_btn.clicked.connect(self.onAdd)
        self.autofill_btn = q.QPushButton('Auto fill')
        self.autofill_btn.setStyleSheet('padding: 2px 5px;')
        self.autofill_btn.clicked.connect(self.autofillRequested)
        box = q.QHBoxLayout()
        label = q.QLabel('Parameters')
        label.setStyleSheet('font-weight: bold;')
        box.addWidget(label, stretch=1)
        if has_autofill_btn:
            box.addWidget(self.autofill_btn)
        box.addWidget(self.add_btn)

        layout = q.QVBoxLayout(self)
        layout.addLayout(box)
        layout.addWidget(self.tview, stretch=1)

    def onAdd(self) -> None:
        dialog = ContainerAddItemDialog(self, self.model)
        dialog.exec_()

    def onRemove(self, idx) -> None:
        self.model.removeRow(idx.row())

    def onConvertToArgument(self, idx) -> None:
        self.model.changeTypeToArgument(idx.row())

    def addActionBuilder(self, fn) -> None:
        self.action_builders.append(fn)

    def onContextMenu(self, pos) -> None:
        smodel = self.tview.selectionModel()
        if not smodel.selectedIndexes():
            return
        idx = smodel.selectedIndexes()[0]
        menu = q.QMenu()
        menu.addAction('Convert to &argument', lambda: self.onConvertToArgument(idx))
        menu.addAction('&Remove item', lambda: self.onRemove(idx))
        for builder in self.action_builders:
            builder(menu, idx)
        menu.exec_(self.sender().viewport().mapToGlobal(pos))
