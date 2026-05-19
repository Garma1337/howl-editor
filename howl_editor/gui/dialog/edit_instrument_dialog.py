# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout,
)

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.gui.layout import WindowSize
from howl_editor.ps1 import spu


@dataclass(frozen=True)
class EditInstrumentResult:
    volume: int
    frequency: int


class EditInstrumentDialog(QDialog):

    def __init__(
        self,
        parent,
        title: str,
        subject_label: str,
        initial_volume: int,
        initial_frequency: int,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(WindowSize.EDIT_INSTRUMENT_WIDTH, WindowSize.EDIT_INSTRUMENT_HEIGHT)
        self._build_ui(subject_label, initial_volume, initial_frequency)

    def chosen(self) -> EditInstrumentResult:
        return EditInstrumentResult(
            volume=self._volume.value(),
            frequency=self._frequency.value(),
        )

    def _build_ui(self, subject_label: str, initial_volume: int, initial_frequency: int) -> None:
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

        self._frequency = QSpinBox()
        self._frequency.setRange(0, cseq_fmt.MAX_PITCH_REGISTER)
        self._frequency.setValue(max(0, min(cseq_fmt.MAX_PITCH_REGISTER, initial_frequency)))
        self._frequency.valueChanged.connect(self._update_hz_label)
        form.addRow("Pitch register:", self._frequency)

        self._hz_label = QLabel()
        self._hz_label.setAlignment(Qt.AlignRight)
        form.addRow("≈ Hz:", self._hz_label)
        self._update_hz_label(self._frequency.value())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)

    def _update_hz_label(self, raw: int) -> None:
        hz = int(raw / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)
        self._hz_label.setText(f"{hz} Hz")
