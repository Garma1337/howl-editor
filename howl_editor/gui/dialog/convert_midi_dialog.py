# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QDialogButtonBox, QCheckBox,
)

from howl_editor.audio.vag_sample_rate_provider import VagSampleRateProvider
from howl_editor.gui.layout import WindowSize
from howl_editor.midi.drum_name_resolver import DrumNameResolver
from howl_editor.midi.models import (
    MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping,
    DrumPitchMapping,
)

_COL_LABEL = 0
_COL_NOTES = 1
_COL_SPU = 2
_COL_FREQ = 3
_COL_DRUM = 4


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
        bank_spu_order: list[int] | None = None,
        spu_sample_rates: dict[int, int] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Convert MIDI to CSEQ - Instrument Mapping")
        self.resize(WindowSize.CONVERT_MIDI_WIDTH, WindowSize.CONVERT_MIDI_HEIGHT)
        self.midi_info = midi_info
        self._max_spu = max_spu_index
        self._drum_names = drum_names or DrumNameResolver()
        self._bank_spu_order = bank_spu_order
        self._spu_sample_rates = spu_sample_rates or {}
        self._drum_override: dict[int, bool] = {}
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Track / Drum hit", "Notes", "SPU Sample ID", "Frequency (Hz)", "Drum"],
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self._fill_table()

        layout.addWidget(self.table)
        group.setLayout(layout)

        return group

    def _build_help_label(self) -> QLabel:
        label = QLabel(
            "Drum tracks on MIDI channel 10 are expanded into one row per "
            "unique drum hit — each needs its own SPU sample. If your "
            "percussion is on another channel, tick 'Drum' to expand it the "
            "same way.",
        )
        label.setWordWrap(True)
        label.setStyleSheet("color: palette(mid); font-size: 11px;")

        return label

    def _fill_table(self) -> None:
        """(Re)build every row from the current drum-override state. Called on
        construction and whenever a Drum toggle changes a track's layout."""
        self._row_meta = self._plan_rows()
        self.table.clearContents()
        self.table.setRowCount(len(self._row_meta))

        for row, meta in enumerate(self._row_meta):
            self._populate_row(row, meta)

        self.table.resizeColumnsToContents()

    def _plan_rows(self) -> list[ConvertRowMeta]:
        """Decide the row layout — one row per melodic track, one row per
        (drum track, drum pitch) for drum tracks. Drum-ness is the channel-10
        auto-detection unless the user overrode it via the Drum toggle."""
        meta: list[ConvertRowMeta] = []

        for track in self.midi_info.tracks:
            if track.note_count == 0:
                continue

            if self._track_is_drum(track):
                pitches = self._drum_pitches_for(track)

                if pitches:
                    for pitch in pitches:
                        meta.append(ConvertRowMeta(
                            midi_track_index=track.index,
                            drum_pitch=pitch,
                            is_drum_track=True,
                        ))

                    continue

            meta.append(ConvertRowMeta(
                midi_track_index=track.index,
                drum_pitch=None,
                is_drum_track=False,
            ))

        return meta

    def _track_is_drum(self, track: MidiTrackInfo) -> bool:
        return self._drum_override.get(track.index, bool(track.drum_pitches))

    def _drum_pitches_for(self, track: MidiTrackInfo) -> list[int]:
        """Pitch list to expand into percussion slots — the channel-10 pitches
        when auto-detected, otherwise every pitch the track plays (for a
        manually flagged drum track)."""
        return track.drum_pitches or track.all_pitches

    def _populate_row(self, row: int, meta: ConvertRowMeta) -> None:
        track = self._track_for(meta.midi_track_index)

        label_text = self._row_label(row, track, meta)
        name_item = QTableWidgetItem(label_text)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, _COL_LABEL, name_item)

        notes_text = self._row_note_count(track, meta)
        notes_item = QTableWidgetItem(str(notes_text))
        notes_item.setFlags(notes_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, _COL_NOTES, notes_item)

        default_spu = self._default_spu_for_row(row)
        spu_spin = QSpinBox()
        spu_spin.setRange(0, 65535)
        spu_spin.setValue(default_spu)
        self.table.setCellWidget(row, _COL_SPU, spu_spin)

        freq_spin = QSpinBox()
        freq_spin.setRange(100, 44100)
        freq_spin.setValue(self._default_freq_hz_for_spu(default_spu))
        self.table.setCellWidget(row, _COL_FREQ, freq_spin)

        spu_spin.valueChanged.connect(
            lambda value, fs=freq_spin: self._sync_freq_to_spu(value, fs),
        )

        if self._is_first_row_of_track(row):
            self.table.setCellWidget(row, _COL_DRUM, self._build_drum_checkbox(track))

    def _build_drum_checkbox(self, track: MidiTrackInfo) -> QCheckBox:
        box = QCheckBox()
        box.setChecked(self._track_is_drum(track))
        box.setToolTip(
            "Treat this track as drums — expand it into one percussion slot "
            "per pitch instead of a single melodic instrument.",
        )
        box.toggled.connect(
            lambda checked, idx=track.index: self._on_drum_toggled(idx, checked),
        )

        return box

    def _on_drum_toggled(self, track_index: int, checked: bool) -> None:
        self._drum_override[track_index] = checked
        self._fill_table()

    def _is_first_row_of_track(self, row: int) -> bool:
        if row == 0:
            return True

        return (
            self._row_meta[row].midi_track_index
            != self._row_meta[row - 1].midi_track_index
        )

    def _row_label(self, row: int, track: MidiTrackInfo, meta: ConvertRowMeta) -> str:
        if meta.drum_pitch is None:
            return track.name

        drum_label = self._drum_names.get_label(meta.drum_pitch)

        if self._is_first_row_of_track(row):
            return f"{track.name}  🥁  {drum_label} ({meta.drum_pitch})"

        return f"     🥁 {drum_label} ({meta.drum_pitch})"

    def _row_note_count(self, track: MidiTrackInfo, meta: ConvertRowMeta) -> int:
        if meta.drum_pitch is None:
            return track.note_count

        # No per-pitch event count tracked yet — total notes is still useful as
        # a rough indicator and avoids another MIDI scan in the dialog.
        return track.note_count

    def _track_for(self, midi_index: int) -> MidiTrackInfo:
        return self.midi_info.tracks[midi_index]

    def _default_freq_hz_for_spu(self, spu: int) -> int:
        """The sample's known playback rate, so the Frequency column prefills
        alongside the SPU. Falls back to the default rate when the SPU has no
        looked-up rate (unknown bank, or a SPU the user typed by hand)."""
        return self._spu_sample_rates.get(spu, VagSampleRateProvider.DEFAULT_RATE)

    def _sync_freq_to_spu(self, spu: int, freq_spin: QSpinBox) -> None:
        """Update the frequency to match a newly chosen SPU, but only when that
        SPU has a known rate — otherwise leave whatever the user has entered."""
        if spu in self._spu_sample_rates:
            freq_spin.setValue(self._spu_sample_rates[spu])

    def _default_spu_for_row(self, row: int) -> int:
        """Prefill SPU sample IDs so a music maker can usually accept the
        defaults. When the song's paired bank is known, use that bank's sample
        SPU indices in order (the tracks are expected to mirror the bank);
        otherwise fall back to a sequential 0,1,2… within the SPU range."""
        if self._bank_spu_order and row < len(self._bank_spu_order):
            return self._bank_spu_order[row]

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
            spu = self.table.cellWidget(row, _COL_SPU).value()
            freq_hz = self.table.cellWidget(row, _COL_FREQ).value()
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
