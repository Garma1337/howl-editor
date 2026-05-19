# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout,
)

from howl_editor.gui.layout import WindowSize
from howl_editor.midi.exporter import MidiExportOptions


class MidiExportOptionsDialog(QDialog):

    def __init__(self, parent, defaults: MidiExportOptions = MidiExportOptions()):
        super().__init__(parent)
        self.setWindowTitle("MIDI export options")
        self.resize(WindowSize.MIDI_EXPORT_WIDTH, WindowSize.MIDI_EXPORT_HEIGHT)
        self._build_ui(defaults)

    def chosen(self) -> MidiExportOptions:
        return MidiExportOptions(
            include_volume_events=self._include_volume.isChecked(),
            apply_instrument_volume=self._apply_inst.isChecked(),
        )

    def _build_ui(self, defaults: MidiExportOptions) -> None:
        layout = QVBoxLayout(self)

        prompt = QLabel("Adjust how this MIDI is written.")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        self._include_volume = QCheckBox("Include in-song volume changes (CC#7)")
        self._include_volume.setChecked(defaults.include_volume_events)
        self._include_volume.setToolTip("When off, mid-song volume changes are dropped so the DAW hears raw note velocities.")
        layout.addWidget(self._include_volume)

        self._apply_inst = QCheckBox("Apply each track's instrument volume at start")
        self._apply_inst.setChecked(defaults.apply_instrument_volume)
        self._apply_inst.setToolTip("When on, each track gets a CC#7 volume set from the instrument it's bound to.")
        layout.addWidget(self._apply_inst)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignRight)
