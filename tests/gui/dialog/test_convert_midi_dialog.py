# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.gui.dialog.convert_midi_dialog import ConvertMidiDialog
from howl_editor.midi.models import MidiInfo, MidiTrackInfo


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _info(num_tracks: int) -> MidiInfo:
    tracks = [
        MidiTrackInfo(index=i, name=f"Track {i}", note_count=10, channels=[0])
        for i in range(num_tracks)
    ]

    return MidiInfo(num_tracks=num_tracks, tracks=tracks)


def _spu_values(dialog: ConvertMidiDialog) -> list[int]:
    return [
        dialog.table.cellWidget(row, 2).value()
        for row in range(dialog.table.rowCount())
    ]


class TestSpuPrefill:

    def test_sequential_within_range(self, qt_app):
        dlg = ConvertMidiDialog(None, _info(4), max_spu_index=10)

        assert _spu_values(dlg) == [0, 1, 2, 3]

    def test_clamps_to_last_valid_index(self, qt_app):
        # MIDI has 5 tracks but the HWL only has 3 SPU entries (indices 0-2).
        dlg = ConvertMidiDialog(None, _info(5), max_spu_index=3)

        assert _spu_values(dlg) == [0, 1, 2, 2, 2]

    def test_zero_when_no_spu_entries(self, qt_app):
        dlg = ConvertMidiDialog(None, _info(3), max_spu_index=0)

        assert _spu_values(dlg) == [0, 0, 0]

    def test_settings_picks_up_prefilled_values(self, qt_app):
        dlg = ConvertMidiDialog(None, _info(3), max_spu_index=10)
        settings = dlg.get_settings()

        sample_ids = [m.sample_id for m in settings.mappings]
        assert sample_ids == [0, 1, 2]


def _info_with_drum_pitches(track_drum_pitches: list[list[int]]) -> MidiInfo:
    tracks = [
        MidiTrackInfo(
            index=i, name=f"Track {i}", note_count=max(len(p), 1),
            channels=[9] if p else [0],
            drum_pitches=p,
        )
        for i, p in enumerate(track_drum_pitches)
    ]

    return MidiInfo(num_tracks=len(track_drum_pitches), tracks=tracks)


def _row_labels(dialog: ConvertMidiDialog) -> list[str]:
    return [
        dialog.table.item(row, 0).text()
        for row in range(dialog.table.rowCount())
    ]


class TestDrumPitchExpansion:
    """Drum tracks expand into one row per unique pitch — each maps to its
    own CseqPercussion slot. CTR-tools does the same when importing MIDI."""

    def test_drum_track_creates_one_row_per_pitch(self, qt_app):
        dlg = ConvertMidiDialog(None, _info_with_drum_pitches([[36, 38, 42]]), max_spu_index=10)

        assert dlg.table.rowCount() == 3

    def test_drum_labels_show_gm_drum_names(self, qt_app):
        dlg = ConvertMidiDialog(None, _info_with_drum_pitches([[36, 38, 42]]), max_spu_index=10)
        labels = _row_labels(dlg)

        assert "Kick" in labels[0]
        assert "Snare" in labels[1]
        assert "Closed Hi-Hat" in labels[2]

    def test_melodic_and_drum_tracks_mixed(self, qt_app):
        # Track 0 = melody, Track 1 = drums with 2 pitches → 3 rows total.
        dlg = ConvertMidiDialog(
            None, _info_with_drum_pitches([[], [36, 38]]), max_spu_index=10,
        )

        assert dlg.table.rowCount() == 3

    def test_settings_emit_per_pitch_drum_mappings(self, qt_app):
        dlg = ConvertMidiDialog(None, _info_with_drum_pitches([[36, 38, 42]]), max_spu_index=10)
        settings = dlg.get_settings()
        mapping = settings.mappings[0]

        assert mapping.is_drum is True
        assert [p.midi_pitch for p in mapping.drum_pitches] == [36, 38, 42]
        # Sequential SPU prefill flows into per-pitch mappings.
        assert [p.sample_id for p in mapping.drum_pitches] == [0, 1, 2]

    def test_settings_for_melodic_track_keeps_single_mapping(self, qt_app):
        dlg = ConvertMidiDialog(None, _info_with_drum_pitches([[]]), max_spu_index=10)
        settings = dlg.get_settings()
        mapping = settings.mappings[0]

        assert mapping.is_drum is False
        assert mapping.drum_pitches == []
        assert mapping.sample_id == 0


def _melodic_track_with_pitches(pitches: list[int]) -> MidiInfo:
    track = MidiTrackInfo(
        index=0, name="Perc off ch10", note_count=len(pitches),
        channels=[3], drum_pitches=[], all_pitches=pitches,
    )

    return MidiInfo(num_tracks=1, tracks=[track])


class TestManualDrumToggle:
    """Percussion not on GM channel 10 is not auto-detected, so it would
    collapse to one melodic instrument. The Drum toggle re-expands it into one
    percussion slot per pitch using the track's full pitch set."""

    def test_starts_as_single_melodic_row(self, qt_app):
        dlg = ConvertMidiDialog(None, _melodic_track_with_pitches([40, 41, 42]), max_spu_index=10)

        assert dlg.table.rowCount() == 1
        assert dlg.get_settings().mappings[0].is_drum is False

    def test_toggling_drum_expands_to_one_row_per_pitch(self, qt_app):
        dlg = ConvertMidiDialog(None, _melodic_track_with_pitches([40, 41, 42]), max_spu_index=10)

        dlg._on_drum_toggled(0, True)

        assert dlg.table.rowCount() == 3
        mapping = dlg.get_settings().mappings[0]
        assert mapping.is_drum is True
        assert [p.midi_pitch for p in mapping.drum_pitches] == [40, 41, 42]

    def test_untoggling_collapses_back_to_melodic(self, qt_app):
        dlg = ConvertMidiDialog(None, _melodic_track_with_pitches([40, 41]), max_spu_index=10)

        dlg._on_drum_toggled(0, True)
        dlg._on_drum_toggled(0, False)

        assert dlg.table.rowCount() == 1
        assert dlg.get_settings().mappings[0].is_drum is False


class TestBankSpuPrefill:
    """When the song's paired bank is known, SPU IDs prefill from the bank's
    sample order so tracks laid out to mirror the bank map across untouched."""

    def test_prefills_from_bank_order(self, qt_app):
        dlg = ConvertMidiDialog(
            None, _info(3), max_spu_index=99, bank_spu_order=[12, 7, 30],
        )

        assert _spu_values(dlg) == [12, 7, 30]

    def test_falls_back_to_sequential_beyond_bank_length(self, qt_app):
        # More MIDI rows than bank samples → extra rows use the sequential
        # clamp against max_spu_index.
        dlg = ConvertMidiDialog(
            None, _info(4), max_spu_index=10, bank_spu_order=[5, 6],
        )

        assert _spu_values(dlg) == [5, 6, 2, 3]

    def test_settings_carry_bank_prefilled_ids(self, qt_app):
        dlg = ConvertMidiDialog(
            None, _info(2), max_spu_index=99, bank_spu_order=[8, 4],
        )

        assert [m.sample_id for m in dlg.get_settings().mappings] == [8, 4]


def _pitch_values(dialog: ConvertMidiDialog) -> list[int]:
    return [
        dialog.table.cellWidget(row, 3).value()
        for row in range(dialog.table.rowCount())
    ]


class TestBasePitchPrefill:
    """The base-pitch column prefills from the pitch each prefilled SPU is
    already played at elsewhere in the file, so the music maker starts from a
    value known to work. Changing the SPU carries its pitch across too.

    The column is the SPU pitch register, never a sample rate: the correct
    value depends on the musical pitch of the recording, which the file does
    not record, so nothing here may silently invent one."""

    def test_prefills_pitch_from_referenced_pitch(self, qt_app):
        dlg = ConvertMidiDialog(
            None, _info(3), max_spu_index=99,
            bank_spu_order=[12, 7, 30],
            spu_base_pitches={12: 2048, 7: 4096, 30: 1024},
        )

        assert _pitch_values(dlg) == [2048, 4096, 1024]

    def test_defaults_when_pitch_unknown(self, qt_app):
        # Nothing references these SPUs → every row falls back to the default.
        dlg = ConvertMidiDialog(None, _info(2), max_spu_index=10)

        assert _pitch_values(dlg) == [cseq_fmt.DEFAULT_BASE_PITCH] * 2

    def test_changing_spu_updates_pitch(self, qt_app):
        dlg = ConvertMidiDialog(
            None, _info(1), max_spu_index=99,
            bank_spu_order=[12],
            spu_base_pitches={12: 2048, 5: 4096},
        )

        dlg.table.cellWidget(0, 2).setValue(5)

        assert _pitch_values(dlg) == [4096]

    def test_unknown_spu_leaves_pitch_untouched(self, qt_app):
        dlg = ConvertMidiDialog(
            None, _info(1), max_spu_index=99,
            bank_spu_order=[12],
            spu_base_pitches={12: 2048},
        )

        dlg.table.cellWidget(0, 2).setValue(999)  # nothing references it

        assert _pitch_values(dlg) == [2048]

    def test_settings_carry_pitch_register_unconverted(self, qt_app):
        # The register reaches the mapping as-is — no Hz round trip to truncate.
        dlg = ConvertMidiDialog(
            None, _info(1), max_spu_index=99,
            bank_spu_order=[7],
            spu_base_pitches={7: 2755},
        )

        assert dlg.get_settings().mappings[0].frequency == 2755

    def test_pitch_range_covers_the_whole_register(self, qt_app):
        dlg = ConvertMidiDialog(None, _info(1), max_spu_index=10)
        spin = dlg.table.cellWidget(0, 3)

        assert (spin.minimum(), spin.maximum()) == (0, cseq_fmt.MAX_PITCH_REGISTER)
