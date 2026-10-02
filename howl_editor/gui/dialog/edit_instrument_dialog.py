# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout,
)

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.voice.pitch_stepper import PitchStepper
from howl_editor.gui.layout import WindowSize
from howl_editor.gui.widget.pitch_spin_box import PitchSpinBox
from howl_editor.ps1 import spu

_CEILING_WARNING = (
    "⚠️ Above the SPU's 4.0× ceiling — the SPU plays it at 4.0× instead, so it comes out flat."
)


@dataclass(frozen=True)
class EditInstrumentResult:
    volume: int
    frequency: int
    adsr: int | None


class EditInstrumentDialog(QDialog):

    def __init__(
        self,
        parent,
        title: str,
        subject_label: str,
        initial_volume: int,
        initial_frequency: int,
        initial_adsr: int | None = None,
        pitch_stepper: PitchStepper | None = None,
    ):
        super().__init__(parent)
        self._stepper = pitch_stepper or PitchStepper()
        self.setWindowTitle(title)
        height = WindowSize.EDIT_INSTRUMENT_HEIGHT_WITH_ADSR if initial_adsr is not None else WindowSize.EDIT_INSTRUMENT_HEIGHT
        self.resize(WindowSize.EDIT_INSTRUMENT_WIDTH, height)
        self._build_ui(subject_label, initial_volume, initial_frequency, initial_adsr)

    def chosen(self) -> EditInstrumentResult:
        adsr: int | None = None

        if self._adsr_lo is not None and self._adsr_hi is not None:
            adsr = (self._adsr_hi.value() << 16) | self._adsr_lo.value()

        return EditInstrumentResult(
            volume=self._volume.value(),
            frequency=self._frequency.value(),
            adsr=adsr,
        )

    def _build_ui(
        self,
        subject_label: str,
        initial_volume: int,
        initial_frequency: int,
        initial_adsr: int | None,
    ) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(subject_label)
        header.setWordWrap(True)
        layout.addWidget(header)

        form = QFormLayout()
        layout.addLayout(form)

        self._volume = QSpinBox()
        self._volume.setRange(0, cseq_fmt.MAX_VOLUME)
        self._volume.setValue(max(0, min(cseq_fmt.MAX_VOLUME, initial_volume)))
        self._volume.setSuffix(f" / {cseq_fmt.MAX_VOLUME}")
        form.addRow("Volume:", self._volume)

        self._frequency = PitchSpinBox(pitch_stepper=self._stepper)
        self._frequency.setValue(max(0, min(cseq_fmt.MAX_PITCH_REGISTER, initial_frequency)))
        self._frequency.valueChanged.connect(self._update_hz_label)
        form.addRow("Pitch register:", self._frequency)
        form.addRow("", self._build_octave_row())

        self._hz_label = QLabel()
        self._hz_label.setAlignment(Qt.AlignRight)
        form.addRow("≈ Hz:", self._hz_label)

        self._ceiling_label = QLabel()
        self._ceiling_label.setWordWrap(True)
        layout.addWidget(self._ceiling_label)

        self._update_hz_label(self._frequency.value())

        self._adsr_lo: QSpinBox | None = None
        self._adsr_hi: QSpinBox | None = None

        if initial_adsr is not None:
            self._adsr_lo = self._make_hex_spinbox(initial_adsr & 0xFFFF)
            self._adsr_hi = self._make_hex_spinbox((initial_adsr >> 16) & 0xFFFF)
            form.addRow("Attack/Decay (ADSR1):", self._adsr_lo)
            form.addRow("Sustain/Release (ADSR2):", self._adsr_hi)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)

    def _build_octave_row(self) -> QHBoxLayout:
        """The spin box already steps octaves on Page Up/Down, but the common
        case deserves something visible."""
        row = QHBoxLayout()

        for label, octaves in (("⬇️ Octave down", -1), ("⬆️ Octave up", 1)):
            button = QPushButton(label)
            button.setToolTip(
                f"{'Halve' if octaves < 0 else 'Double'} the pitch register — "
                f"exactly one octave {'down' if octaves < 0 else 'up'}."
            )
            button.clicked.connect(lambda _checked=False, o=octaves: self._frequency.shift_octaves(o))
            row.addWidget(button)

        row.addStretch()
        return row

    def _make_hex_spinbox(self, initial: int) -> QSpinBox:
        box = QSpinBox()
        box.setRange(0, cseq_fmt.MAX_ADSR_HALF)
        box.setValue(max(0, min(cseq_fmt.MAX_ADSR_HALF, initial)))
        box.setDisplayIntegerBase(16)
        box.setPrefix("0x")
        return box

    def _update_hz_label(self, raw: int) -> None:
        hz = int(raw / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)
        self._hz_label.setText(f"{hz} Hz  ({raw / spu.FREQUENCY_UNIT:.2f}×)")
        self._ceiling_label.setText(
            _CEILING_WARNING if self._stepper.exceeds_playable_ceiling(raw) else "",
        )
