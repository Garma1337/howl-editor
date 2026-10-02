# coding: utf-8

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QGroupBox, QFormLayout, QTableWidget,
    QTableWidgetItem, QDialogButtonBox, QCheckBox,
)

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ctr.voice.pitch_headroom import PitchHeadroomInspector
from howl_editor.ctr.voice.pitch_stepper import PitchStepper
from howl_editor.gui.layout import WindowSize
from howl_editor.gui.widget.pitch_spin_box import PitchSpinBox
from howl_editor.midi.drum_name_resolver import DrumNameResolver
from howl_editor.midi.models import (
    MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping,
    DrumPitchMapping,
)

_COL_LABEL = 0
_COL_NOTES = 1
_COL_SPU = 2
_COL_PITCH = 3
_COL_DRUM = 4

_USER_SET_PITCH = "userSetPitch"

_PITCH_TOOLTIP = (
    "The SPU pitch register this instrument plays at MIDI note 60.\n"
    "4096 plays the sample back at 1.0× speed; halving it drops an "
    "octave, doubling it raises one.\n"
    "The arrows step one semitone; Page Up / Page Down step a whole octave."
)

_FREE_SPU_SUFFIX = "  🆓 free"
_FREE_SPU_TOOLTIP = (
    "Free slot — no bank holds a sample here, so this instrument would play silence."
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
        bank_spu_order: list[int] | None = None,
        spu_base_pitches: dict[int, int] | None = None,
        pitch_headroom: PitchHeadroomInspector | None = None,
        free_spu_indices: set[int] | None = None,
        pitch_stepper: PitchStepper | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Convert MIDI to CSEQ - Instrument Mapping")
        self.resize(WindowSize.CONVERT_MIDI_WIDTH, WindowSize.CONVERT_MIDI_HEIGHT)
        self.midi_info = midi_info
        self._max_spu = max_spu_index
        self._drum_names = drum_names or DrumNameResolver()
        self._bank_spu_order = bank_spu_order
        self._spu_base_pitches = spu_base_pitches or {}
        self._free_spu = free_spu_indices or set()
        self._stepper = pitch_stepper or PitchStepper()
        self._headroom = pitch_headroom or PitchHeadroomInspector(PitchCalculator())
        self._drum_override: dict[int, bool] = {}
        self._row_meta: list[ConvertRowMeta] = []
        self._warning_label = self._build_warning_label()

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_info_group())
        layout.addLayout(self._build_bpm_row())
        layout.addWidget(self._build_mapping_group())
        layout.addWidget(self._warning_label)
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
            ["Track / Drum hit", "Notes", "SPU Sample ID", "Base pitch (note 60)", "Drum"],
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
        self._refresh_pitch_warnings()

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
        self._mark_free_spu(spu_spin)
        spu_spin.valueChanged.connect(lambda _value, s=spu_spin: self._mark_free_spu(s))
        self.table.setCellWidget(row, _COL_SPU, spu_spin)

        pitch_spin = PitchSpinBox(pitch_stepper=self._stepper)
        pitch_spin.setValue(self._default_pitch_for_spu(default_spu))
        pitch_spin.setToolTip(_PITCH_TOOLTIP)
        self.table.setCellWidget(row, _COL_PITCH, pitch_spin)

        pitch_spin.valueChanged.connect(
            lambda _value, ps=pitch_spin: ps.setProperty(_USER_SET_PITCH, True),
        )
        pitch_spin.valueChanged.connect(lambda *_: self._refresh_pitch_warnings())
        spu_spin.valueChanged.connect(
            lambda value, ps=pitch_spin: self._sync_pitch_to_spu(value, ps),
        )
        spu_spin.valueChanged.connect(lambda *_: self._refresh_pitch_warnings())

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

    def _mark_free_spu(self, spin: QSpinBox) -> None:
        """Flag a free slot in place: no bank holds a sample there, so the
        instrument would play silence."""
        if spin.value() in self._free_spu:
            spin.setSuffix(_FREE_SPU_SUFFIX)
            spin.setToolTip(_FREE_SPU_TOOLTIP)
        else:
            spin.setSuffix("")
            spin.setToolTip("")

    def _default_pitch_for_spu(self, spu: int) -> int:
        """The base pitch this sample is already played at elsewhere in the
        file, so the column prefills with a value known to work rather than a
        guess. Falls back to the neutral default only when nothing references
        the SPU yet."""
        return self._spu_base_pitches.get(spu, cseq_fmt.DEFAULT_BASE_PITCH)

    def _sync_pitch_to_spu(self, spu: int, pitch_spin: QSpinBox) -> None:
        """Carry a newly chosen SPU's existing base pitch across, but never
        over a pitch the user set by hand.

        Rows deliberately pointed at the same sample at different pitches are
        the supported way to get pitched variants of one sample, so silently
        resetting an edited pitch when the SPU changes would fight exactly the
        workflow this dialog needs to support. Once a row's pitch has been
        touched, it is the user's."""
        if spu not in self._spu_base_pitches:
            return

        if pitch_spin.property(_USER_SET_PITCH):
            return

        previous = pitch_spin.blockSignals(True)
        pitch_spin.setValue(self._spu_base_pitches[spu])
        pitch_spin.blockSignals(previous)

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

    def _build_warning_label(self) -> QLabel:
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet("color: #e6b800; font-size: 11px;")
        label.hide()

        return label

    def _refresh_pitch_warnings(self) -> None:
        """Re-evaluate every melodic row against the notes its track plays and
        surface any that will break in game at the chosen base pitch. Drum rows
        are skipped: a drum's note picks which percussion, so its pitch is never
        scaled up into the wrap the way a melodic keyboard's top notes are."""
        messages: list[str] = []

        for row, meta in enumerate(self._row_meta):
            spin = self.table.cellWidget(row, _COL_PITCH)
            if spin is None:
                continue

            if meta.is_drum_track:
                self._clear_pitch_alarm(spin)
                continue

            track = self._track_for(meta.midi_track_index)
            headroom = self._headroom.inspect(spin.value(), track.all_pitches)

            if headroom.is_clean:
                self._clear_pitch_alarm(spin)
                continue

            safe = self._headroom.highest_safe_base_pitch(track.all_pitches)
            text = self._headroom_text(track.name, headroom, safe)
            self._set_pitch_alarm(spin, text)
            messages.append(text)

        self._show_warnings(messages)

    def _headroom_text(self, name: str, headroom, safe: int | None) -> str:
        effect = "wrap to garbage in game" if headroom.garbage else "play flat"

        return (
            f"“{name}”: the top {headroom.affected_notes} note(s) exceed the "
            f"SPU pitch ceiling and will {effect}. Lower the base pitch to "
            f"{safe} or less (or raise the sample's own pitch instead)."
        )

    def _set_pitch_alarm(self, spin: QSpinBox, text: str) -> None:
        spin.setStyleSheet("QSpinBox { background: #6b1f1f; color: white; }")
        spin.setToolTip(text)

    def _clear_pitch_alarm(self, spin: QSpinBox) -> None:
        spin.setStyleSheet("")
        spin.setToolTip(_PITCH_TOOLTIP)

    def _show_warnings(self, messages: list[str]) -> None:
        if not messages:
            self._warning_label.clear()
            self._warning_label.hide()
            return

        self._warning_label.setText("\n".join(f"⚠️ {m}" for m in messages))
        self._warning_label.show()

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
            freq = self.table.cellWidget(row, _COL_PITCH).value()

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
