# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QCheckBox, QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QDialogButtonBox,
)

from howl_editor.midi.models import MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping


class ConvertMidiDialog(QDialog):

    def __init__(self, parent, midi_info: MidiInfo, max_spu_index: int):
        super().__init__(parent)
        self.setWindowTitle("Convert MIDI to CSEQ - Instrument Mapping")
        self.resize(650, 500)
        self.midi_info = midi_info
        self._max_spu = max_spu_index

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_info_group())
        layout.addLayout(self._build_bpm_row())
        layout.addWidget(self._build_mapping_group())
        layout.addWidget(self._build_buttons())

    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("MIDI File Info")
        form = QFormLayout()
        form.addRow("Tracks:", QLabel(str(self.midi_info.num_tracks)))
        form.addRow("Ticks/Beat:", QLabel(str(self.midi_info.ticks_per_beat)))
        group.setLayout(form)

        return group

    def _build_bpm_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("BPM (0 = from MIDI):"))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(0, 300)
        self.bpm_spin.setValue(0)
        layout.addWidget(self.bpm_spin)
        layout.addStretch()

        return layout

    def _build_mapping_group(self) -> QGroupBox:
        group = QGroupBox("Track Instrument Mapping")
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Track", "Notes", "SPU Sample ID", "Frequency (Hz)", "Drum?"])
        self.table.horizontalHeader().setStretchLastSection(True)

        tracks_with_notes = [t for t in self.midi_info.tracks if t.note_count > 0]
        self.table.setRowCount(len(tracks_with_notes))
        self.track_indices: list[int] = []

        for row, track in enumerate(tracks_with_notes):
            self.track_indices.append(track.index)
            self._populate_row(row, track)

        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        group.setLayout(layout)
        
        return group

    def _populate_row(self, row: int, track: MidiTrackInfo) -> None:
        name_item = QTableWidgetItem(track.name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, name_item)

        notes_item = QTableWidgetItem(str(track.note_count))
        notes_item.setFlags(notes_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, notes_item)

        spu_spin = QSpinBox()
        spu_spin.setRange(0, 65535)
        spu_spin.setValue(self._default_spu_for_row(row))
        self.table.setCellWidget(row, 2, spu_spin)

        freq_spin = QSpinBox()
        freq_spin.setRange(100, 44100)
        freq_spin.setValue(11025)
        self.table.setCellWidget(row, 3, freq_spin)

        drum_check = QCheckBox()
        if 10 in track.channels:
            drum_check.setChecked(True)

        self.table.setCellWidget(row, 4, drum_check)

    def _default_spu_for_row(self, row: int) -> int:
        """Prefill SPU sample IDs sequentially within the available range, so
        a music maker can usually accept the defaults if the bank was filled
        in the same order as the MIDI tracks."""
        if self._max_spu <= 0:
            return 0

        return min(row, self._max_spu - 1)

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def get_settings(self) -> MidiConvertSettings:
        settings = MidiConvertSettings()
        if self.bpm_spin.value() > 0:
            settings.default_bpm = self.bpm_spin.value()

        max_idx = max(self.track_indices, default=-1) + 1
        settings.mappings = [InstrumentMapping() for _ in range(max_idx)]

        for row, midi_idx in enumerate(self.track_indices):
            spu_spin = self.table.cellWidget(row, 2)
            freq_spin = self.table.cellWidget(row, 3)
            drum_check = self.table.cellWidget(row, 4)
            
            settings.mappings[midi_idx] = InstrumentMapping(
                sample_id=spu_spin.value(),
                frequency=int(freq_spin.value() * 4096 / 44100),
                is_drum=drum_check.isChecked(),
            )

        return settings
