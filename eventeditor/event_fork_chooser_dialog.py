from eventeditor.event_chooser_dialog import EventChooserDialog
from eventeditor.flow_data import FlowData
import eventeditor.util as util
from evfl import Event
from evfl.enums import EventType
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtGui as qg # type: ignore
import PyQt5.QtWidgets as q # type: ignore
import typing

class EventForkChooserDialog(q.QDialog):
    chooserEventDoubleClicked = qc.pyqtSignal(int)
    chooserSelectSignal = qc.pyqtSignal(int)

    def __init__(self, parent, flow_data: FlowData) -> None:
        super().__init__(parent)
        self.setWindowTitle('Create fork event')
        self.setMinimumWidth(500)
        self.flow_data = flow_data

        self.start_event: typing.Optional[Event] = None
        self.end_event: typing.Optional[Event] = None

        self.form = q.QFormLayout()
        self.start_event_btn = q.QPushButton('<select an event>')
        self.end_event_btn = q.QPushButton('<select an event>')
        self.form.addRow('Add &fork before:', self.start_event_btn)
        self.form.addRow('Add &join after\n(action or subflow event):', self.end_event_btn)
        self.connectEventButtons()
        self.initLayout()

    def initLayout(self) -> None:
        warning_msg = q.QLabel('<br><b>Warning</b>: no validation will be performed.')
        warning_msg.setTextFormat(qc.Qt.RichText)

        btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Ok | q.QDialogButtonBox.Cancel);
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout = q.QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(warning_msg)
        layout.addWidget(btn_box)

    def connectEventButtons(self) -> None:
        self.start_event_btn.clicked.connect(lambda: self.onEditEventClicked('start_event'))
        self.end_event_btn.clicked.connect(lambda: self.onEditEventClicked('end_event'))

    def onEditEventClicked(self, event_attr_name: str) -> None:
        self.setEnabled(False)
        dialog = EventChooserDialog(self, self.flow_data, enable_ctx_menu=False)
        dialog.show()
        self.chooserSelectSignal.connect(dialog.event_view.selectEvent)
        try:
            dialog.event_view.selectEvent(
                self.flow_data.flow.flowchart.events.index(getattr(self, event_attr_name)))
        except ValueError:
            pass
        dialog.event_view.jumpToFlowchartRequested.connect(self.chooserEventDoubleClicked)
        dialog.finished.connect(lambda: self.setEnabled(True))
        def onChooserAccept():
            selected_event = dialog.getSelectedEvent()
            setattr(self, event_attr_name, selected_event)
            getattr(self, event_attr_name + '_btn').setText(util.get_event_full_description(selected_event))
        dialog.accepted.connect(onChooserAccept)

    def closeEvent(self, event):
        if not self.isEnabled():
            event.ignore()

    def accept(self) -> None:
        if not self.start_event or not self.end_event:
            q.QMessageBox.critical(self, 'Create fork event', 'Please select a start event and an end event.')
            return
        super().accept()

    def getEventPair(self) -> typing.Tuple[Event, Event]:
        """Get the selected start and end events. Only valid if the accepted signal was triggered."""
        return (self.start_event, self.end_event)
