# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QDialogButtonBox,
)

from howl_editor.gui.layout import WindowSize
from howl_editor.midi.drum_name_resolver import DrumNameResolver
from howl_editor.midi.models import (
    MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping,
    DrumPitchMapping,
)


@dataclass
class ConvertRowMeta:
    """Maps a table row back to the (track, drum-pitch) it represents.

    `drum_pitch is None` denotes a melodic-track row (one row per track);
    otherwise the row is one of several drum-pitch sub-rows belonging to the
    same MIDI track."""
    midi_track_index: int
    drum_pitch: int | None
    is_drum_track: bool


class ConvertMidiDialog(QDialog):

    def __init__(
        self, parent, midi_info: MidiInfo, max_spu_index: int,
        drum_names: DrumNameResolver | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Convert MIDI to CSEQ - Instrument Mapping")
        self.resize(WindowSize.CONVERT_MIDI_WIDTH, WindowSize.CONVERT_MIDI_HEIGHT)
        self.midi_info = midi_info
        self._max_spu = max_spu_index
        self._drum_names = drum_names or DrumNameResolver()
        self._row_meta: list[ConvertRowMeta] = []

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

        layout.addWidget(self._build_help_label())

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Track / Drum hit", "Notes", "SPU Sample ID", "Frequency (Hz)"],
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self._row_meta = self._plan_rows()
        self.table.setRowCount(len(self._row_meta))

        for row, meta in enumerate(self._row_meta):
            self._populate_row(row, meta)

        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        group.setLayout(layout)

        return group

    def _build_help_label(self) -> QLabel:
        label = QLabel(
            "Drum tracks on MIDI channel 10 are expanded into one row per "
            "unique drum hit — each needs its own SPU sample.",
        )
        label.setWordWrap(True)
        label.setStyleSheet("color: palette(mid); font-size: 11px;")

        return label

    def _plan_rows(self) -> list[ConvertRowMeta]:
        """Decide the row layout before building widgets — one row per melodic
        track, one row per (drum track, drum pitch) for drum tracks."""
        meta: list[ConvertRowMeta] = []

        for track in self.midi_info.tracks:
            if track.note_count == 0:
                continue

            if track.drum_pitches:
                for pitch in track.drum_pitches:
                    meta.append(ConvertRowMeta(
                        midi_track_index=track.index,
                        drum_pitch=pitch,
                        is_drum_track=True,
                    ))
            else:
                meta.append(ConvertRowMeta(
                    midi_track_index=track.index,
                    drum_pitch=None,
                    is_drum_track=False,
                ))

        return meta

    def _populate_row(self, row: int, meta: ConvertRowMeta) -> None:
        track = self._track_for(meta.midi_track_index)

        label_text = self._row_label(track, meta)
        name_item = QTableWidgetItem(label_text)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, name_item)

        notes_text = self._row_note_count(track, meta)
        notes_item = QTableWidgetItem(str(notes_text))
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

    def _row_label(self, track: MidiTrackInfo, meta: ConvertRowMeta) -> str:
        if meta.drum_pitch is None:
            return track.name

        drum_label = self._drum_names.get_label(meta.drum_pitch)
        first_drum_row = self._is_first_drum_row(meta)

        if first_drum_row:
            return f"{track.name}  🥁  {drum_label} ({meta.drum_pitch})"

        return f"     🥁 {drum_label} ({meta.drum_pitch})"

    def _is_first_drum_row(self, meta: ConvertRowMeta) -> bool:
        for other in self._row_meta:
            if other.midi_track_index != meta.midi_track_index:
                continue

            return other is meta or other.drum_pitch == meta.drum_pitch

        return False

    def _row_note_count(self, track: MidiTrackInfo, meta: ConvertRowMeta) -> int:
        if meta.drum_pitch is None:
            return track.note_count

        # No per-pitch event count tracked yet — total notes is still useful as
        # a rough indicator and avoids another MIDI scan in the dialog.
        return track.note_count

    def _track_for(self, midi_index: int) -> MidiTrackInfo:
        return self.midi_info.tracks[midi_index]

    def _default_spu_for_row(self, row: int) -> int:
        """Prefill SPU sample IDs sequentially within the available range, so
        a music maker can usually accept the defaults if the bank was filled
        in the same order as the MIDI tracks (and drum hits)."""
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

        max_idx = max((m.midi_track_index for m in self._row_meta), default=-1) + 1
        settings.mappings = [InstrumentMapping() for _ in range(max_idx)]

        for row, meta in enumerate(self._row_meta):
            spu = self.table.cellWidget(row, 2).value()
            freq_hz = self.table.cellWidget(row, 3).value()
            freq = int(freq_hz * 4096 / 44100)

            if meta.is_drum_track:
                mapping = settings.mappings[meta.midi_track_index]
                mapping.is_drum = True
                mapping.drum_pitches.append(DrumPitchMapping(
                    midi_pitch=meta.drum_pitch,
                    sample_id=spu,
                    frequency=freq,
                ))
            else:
                settings.mappings[meta.midi_track_index] = InstrumentMapping(
                    sample_id=spu,
                    frequency=freq,
                    is_drum=False,
                )

        return settings
