import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class SearchBar(q.QWidget):
    textChanged = qc.pyqtSignal(str)
    caseInsensitiveChanged = qc.pyqtSignal(bool)

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.close_btn = q.QPushButton()
        self.close_btn.setIcon(self.style().standardIcon(q.QStyle.SP_DialogCloseButton))

        self.box = q.QLineEdit()
        self.box.setPlaceholderText('Search…')

        self.caseInsensitiveCbox = q.QCheckBox('Case insensitive')
        self.caseInsensitiveCbox.setChecked(True)

        layout = q.QHBoxLayout(self)
        layout.addWidget(self.close_btn)
        layout.addWidget(self.box)
        layout.addWidget(self.caseInsensitiveCbox)
        layout.setStretch(1, 1)
        layout.setContentsMargins(5, 5, 5, 5)

        self.close_btn.clicked.connect(self.hideAndClear)
        close_action = q.QAction(self)
        close_action.setShortcut(qg.QKeySequence.Cancel)
        close_action.triggered.connect(self.hideAndClear)
        self.addAction(close_action)

        self.box.textChanged.connect(self.textChanged)

        self.caseInsensitiveCbox.stateChanged.connect(lambda state: self.caseInsensitiveChanged.emit(state == qc.Qt.Checked))

    def hideAndClear(self) -> None:
        self.close()
        self.box.clear()

    def showAndFocus(self) -> None:
        self.show()
        self.box.setFocus()

    def setValue(self, value: str) -> None:
        self.box.setText(value)

    def addFindShortcut(self, widget) -> None:
        find_action = q.QAction(widget)
        find_action.setShortcut(qg.QKeySequence.Find)
        find_action.triggered.connect(self.showAndFocus)
        widget.addAction(find_action)

    def connectToFilterModel(self, model) -> None:
        self.textChanged.connect(model.setFilterFixedString)
        def setModelFilterCaseSensitivity(insensitive: bool) -> None:
            model.setFilterCaseSensitivity(qc.Qt.CaseInsensitive if insensitive else qc.Qt.CaseSensitive)
        self.caseInsensitiveChanged.connect(setModelFilterCaseSensitivity)
        setModelFilterCaseSensitivity(self.caseInsensitiveCbox.isChecked())
