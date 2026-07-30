# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox,
    QVBoxLayout,
)

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import CseqEventType
from howl_editor.gui.layout import WindowSize

_EVENT_LABELS: dict[CseqEventType, str] = {
    CseqEventType.NOTE_ON: "Note on (0x05)",
    CseqEventType.NOTE_OFF: "Note off (0x01)",
    CseqEventType.VELOCITY: "Volume (0x06)",
    CseqEventType.PAN: "Pan (0x07)",
    CseqEventType.REVERB: "Reverb (0x08)",
    CseqEventType.CHANGE_PATCH: "Change instrument (0x09)",
    CseqEventType.PITCH_BEND: "Pitch bend (0x0A)",
}

_NOTE_EVENTS = (CseqEventType.NOTE_ON, CseqEventType.NOTE_OFF)


@dataclass(frozen=True)
class EventEditResult:
    event_type: CseqEventType
    pitch: int
    velocity: int
    delta: int


class EditEventDialog(QDialog):
    """Edit one CSEQ event's parameter bytes, or build a new one to insert.

    Passing `event_type` pins the dialog to that opcode (edit mode); passing
    None lets the user pick one (insert mode). `is_drum` changes how the first
    parameter of a note event is labelled, because on a drum track that byte
    is an index into the percussion table rather than a musical pitch — which
    is the whole reason a newly added percussion descriptor is reachable.
    """

    def __init__(
        self,
        parent,
        event_type: CseqEventType | None,
        pitch: int,
        velocity: int = 0,
        delta: int = 0,
        is_drum: bool = False,
        descriptor_count: int = 0,
    ):
        super().__init__(parent)
        self._insert_mode = event_type is None
        self._is_drum = is_drum
        self._descriptor_count = descriptor_count
        self.setWindowTitle("Insert event" if self._insert_mode else "Edit event")
        self.resize(
            WindowSize.EDIT_INSTRUMENT_WIDTH,
            WindowSize.EDIT_INSTRUMENT_HEIGHT_WITH_ADSR,
        )
        self._build_ui(event_type, pitch, velocity, delta)

    def chosen(self) -> EventEditResult:
        return EventEditResult(
            event_type=self._current_type(),
            pitch=self._pitch.value(),
            velocity=self._velocity.value(),
            delta=self._delta.value(),
        )

    def _build_ui(
        self, event_type: CseqEventType | None, pitch: int, velocity: int, delta: int,
    ) -> None:
        layout = QVBoxLayout(self)

        self._blurb = QLabel()
        self._blurb.setWordWrap(True)
        layout.addWidget(self._blurb)

        form = QFormLayout()
        layout.addLayout(form)

        self._type_combo: QComboBox | None = None
        self._fixed_type = event_type

        if self._insert_mode:
            self._type_combo = QComboBox()
            for kind, label in _EVENT_LABELS.items():
                self._type_combo.addItem(label, kind)

            self._type_combo.currentIndexChanged.connect(self._refresh)
            form.addRow("Event:", self._type_combo)
        else:
            form.addRow("Event:", QLabel(_EVENT_LABELS.get(event_type, str(event_type))))

        self._pitch = QSpinBox()
        self._pitch.setRange(0, cseq_fmt.CC_MAX)
        self._pitch.setValue(max(0, min(cseq_fmt.CC_MAX, pitch)))
        self._pitch.valueChanged.connect(self._refresh)
        self._pitch_row_label = QLabel("Value:")
        form.addRow(self._pitch_row_label, self._pitch)

        self._hint = QLabel()
        self._hint.setAlignment(Qt.AlignRight)
        self._hint.setWordWrap(True)
        form.addRow("Meaning:", self._hint)

        self._velocity = QSpinBox()
        self._velocity.setRange(0, cseq_fmt.CC_MAX)
        self._velocity.setValue(max(0, min(cseq_fmt.CC_MAX, velocity)))
        self._velocity_label = QLabel("Velocity:")
        form.addRow(self._velocity_label, self._velocity)

        self._delta = QSpinBox()
        self._delta.setRange(0, 0xFFFF)
        self._delta.setValue(max(0, delta))
        self._delta.setToolTip(
            "Ticks to wait before this event. On an inserted event, 0 places "
            "it at the same tick as the event it sits before, so nothing "
            "later in the track shifts.",
        )
        form.addRow("Delta (ticks):", self._delta)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)

        self._refresh()

    def _current_type(self) -> CseqEventType:
        if self._type_combo is not None:
            return self._type_combo.currentData()

        return self._fixed_type

    def _refresh(self, *_) -> None:
        event_type = self._current_type()

        self._pitch_row_label.setText(self._pitch_label(event_type))
        self._hint.setText(self.describe(event_type, self._pitch.value(), self._is_drum))
        self._blurb.setText(self._blurb_for(event_type))

        # Only NOTE_ON carries a second parameter byte.
        show_velocity = event_type == CseqEventType.NOTE_ON
        self._velocity.setVisible(show_velocity)
        self._velocity_label.setVisible(show_velocity)

    def _pitch_label(self, event_type: CseqEventType) -> str:
        if event_type in _NOTE_EVENTS:
            return "Percussion index:" if self._is_drum else "Note:"

        if event_type == CseqEventType.CHANGE_PATCH:
            return "Instrument index:"

        return "Value:"

    def _blurb_for(self, event_type: CseqEventType) -> str:
        if event_type in _NOTE_EVENTS and self._is_drum:
            known = (
                f" This song has {self._descriptor_count} percussion "
                f"descriptors (0–{self._descriptor_count - 1})."
                if self._descriptor_count else ""
            )

            return (
                "On a drum track this byte is a direct index into the "
                "percussion table — it selects which descriptor sounds and is "
                "never transposed. Point it at a new descriptor to use a "
                f"pitched variant of a sample.{known}"
            )

        if event_type == CseqEventType.CHANGE_PATCH:
            known = (
                f" This song has {self._descriptor_count} instruments "
                f"(0–{self._descriptor_count - 1})."
                if self._descriptor_count else ""
            )

            return (
                "Selects which instrument descriptor the following notes on "
                f"this track use.{known}"
            )

        if event_type in _NOTE_EVENTS:
            return (
                "On a melodic track the note indexes the frequency table and "
                "scales the instrument's base pitch, so one sample covers the "
                "whole keyboard."
            )

        return (
            "This event re-applies to every note already sounding on the "
            "track, not just to notes started after it."
        )

    @staticmethod
    def describe(event_type: CseqEventType, value: int, is_drum: bool = False) -> str:
        """Plain-language reading of an event's parameter byte. Public because
        the track event table shows the same text alongside the raw value."""
        if event_type == CseqEventType.PITCH_BEND:
            # The byte is fixed-point semitones biased so 0x80 is neutral —
            # see cseq.format for the derivation.
            semitones = (
                value / cseq_fmt.PITCH_BEND_FINE_STEPS
            ) - cseq_fmt.PITCH_BEND_SEMITONES_DOWN

            if abs(semitones) < 0.005:
                return "no bend (neutral)"

            return f"{semitones:+.2f} semitones"

        if event_type == CseqEventType.PAN:
            if value == cseq_fmt.PAN_CENTER:
                return "centre"

            side = "left" if value < cseq_fmt.PAN_CENTER else "right"
            return f"{side} ({value} / {cseq_fmt.CC_MAX})"

        if event_type == CseqEventType.VELOCITY:
            return f"{value / cseq_fmt.CC_MAX * 100:.0f}% volume"

        if event_type == CseqEventType.REVERB:
            return "off" if value == 0 else f"level {value} / {cseq_fmt.MAX_REVERB}"

        if event_type in _NOTE_EVENTS:
            return f"percussion #{value}" if is_drum else f"note {value}"

        if event_type == CseqEventType.CHANGE_PATCH:
            return f"instrument #{value}"

        return ""
