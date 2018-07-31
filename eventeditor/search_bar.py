import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore

class SearchBar(q.QWidget):
    textChanged = qc.pyqtSignal(str)

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.close_btn = q.QPushButton()
        self.close_btn.setIcon(self.style().standardIcon(q.QStyle.SP_DialogCloseButton))

        self.box = q.QLineEdit()
        self.box.setPlaceholderText('Search…')

        layout = q.QHBoxLayout(self)
        layout.addWidget(self.close_btn)
        layout.addWidget(self.box)
        layout.setStretch(1, 1)
        layout.setContentsMargins(5, 5, 5, 5)

        self.close_btn.clicked.connect(self.hideAndClear)
        close_action = q.QAction(self)
        close_action.setShortcut(qg.QKeySequence.Cancel)
        close_action.triggered.connect(self.hideAndClear)
        self.addAction(close_action)

        self.box.textChanged.connect(self.textChanged)

    def hideAndClear(self) -> None:
        self.close()
        self.box.clear()

    def showAndFocus(self) -> None:
        self.show()
        self.box.setFocus()

    def setValue(self, value: str) -> None:
        self.box.setText(value)
