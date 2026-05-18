# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

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
