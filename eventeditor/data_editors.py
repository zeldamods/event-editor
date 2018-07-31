import copy
import traceback
import typing
import yaml

import eventeditor.util as util
from evfl import ActorIdentifier
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class ActorIdentifierEditDialog(q.QDialog):
    def __init__(self, parent, identifier: ActorIdentifier) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.setWindowTitle('Edit actor identifier')
        self.setMinimumWidth(500)
        self.identifier = copy.copy(identifier)

        form_layout = q.QFormLayout()
        self.name_box = q.QLineEdit()
        self.name_box.setText(identifier.name)
        form_layout.addRow('&Name:', self.name_box)
        self.sub_name_box = q.QLineEdit()
        self.sub_name_box.setText(identifier.sub_name)
        form_layout.addRow('&Sub name:', self.sub_name_box)

        layout = q.QVBoxLayout(self)
        layout.addLayout(form_layout)
        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);
        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def accept(self) -> None:
        self.identifier.name = self.name_box.text()
        self.identifier.sub_name = self.sub_name_box.text()
        super().accept()

class ArrayEditDialog(q.QDialog):
    def __init__(self, parent, data: list) -> None:
        super().__init__(parent, qc.Qt.WindowTitleHint | qc.Qt.WindowSystemMenuHint)
        self.resize(350, 100)
        self.data = data
        self.setWindowTitle(f'Edit {type(self.data[0]).__name__} array')

        label = q.QLabel('New array data:')
        self.tedit = q.QPlainTextEdit()
        font = qg.QFontDatabase.systemFont(qg.QFontDatabase.FixedFont)
        font.setPointSize(font.pointSize() * 1.05)
        self.tedit.setFont(font)
        self.tedit.setPlainText(yaml.dump(self.data, allow_unicode=True, Dumper=yaml.SafeDumper))

        layout = q.QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(self.tedit)
        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel);
        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def accept(self) -> None:
        try:
            data = yaml.load(self.tedit.toPlainText(), Loader=yaml.SafeLoader)
        except yaml.parser.ParserError as e:
            q.QMessageBox.critical(self, 'Invalid data', f'Could not parse array data. Please verify that the syntax is correct and try again.\n\nDetails:\n\n{e}')
            return

        if not isinstance(data, list):
            q.QMessageBox.critical(self, 'Invalid data', 'Not an array')
            return
        if not data:
            q.QMessageBox.critical(self, 'Invalid data', f'The array must contain at least one element, and all elements should be {type(self.data[0]).__name__}s.')
            return
        if not util.are_list_types_homogeneous_and_equal(self.data, data):
            q.QMessageBox.critical(self, 'Invalid data', f'All elements should be {type(self.data[0]).__name__}s.')
            return

        self.data = data
        super().accept()

def _abstract_item_view_edit(parent, model, index: qc.QModelIndex, trigger, triggers) -> bool:
    if not (triggers & trigger) or not index.isValid() or not (index.flags() & (qc.Qt.ItemIsEditable | qc.Qt.ItemIsUserCheckable)):
        return False

    data = index.data(qc.Qt.UserRole)

    if isinstance(data, ActorIdentifier):
        dialog = ActorIdentifierEditDialog(parent, data)
        if dialog.exec_():
            model.setData(index, dialog.identifier, qc.Qt.EditRole)
        return True

    if isinstance(data, list):
        array_dialog = ArrayEditDialog(parent, data)
        if array_dialog.exec_():
            model.setData(index, array_dialog.data, qc.Qt.EditRole)
        return True

    return False

class CustomTableView(q.QTableView):
    def edit(self, index: qc.QModelIndex, trigger, event) -> bool:
        if _abstract_item_view_edit(self, self.model(), index, trigger, self.editTriggers()):
            return False
        return super().edit(index, trigger, event)
