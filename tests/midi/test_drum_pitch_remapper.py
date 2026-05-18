# coding: utf-8

from dataclasses import dataclass

from howl_editor.midi.drum_pitch_remapper import DrumPitchRemapper


@dataclass
class _Msg:
    type: str
    note: int
    channel: int = 0
    velocity: int = 100


class TestCollectDrumPitches:

    def test_collects_unique_pitches_in_sorted_order(self):
        track = [
            _Msg("note_on", 42, channel=9),
            _Msg("note_on", 36, channel=9),
            _Msg("note_off", 36, channel=9),
            _Msg("note_on", 38, channel=9),
            _Msg("note_on", 36, channel=9),
        ]

        assert DrumPitchRemapper().collect_drum_pitches(track) == [36, 38, 42]

    def test_ignores_non_drum_channels(self):
        track = [
            _Msg("note_on", 36, channel=0),
            _Msg("note_on", 38, channel=9),
        ]

        assert DrumPitchRemapper().collect_drum_pitches(track) == [38]

    def test_empty_when_no_drum_channel_notes(self):
        track = [_Msg("note_on", 60, channel=0)]

        assert DrumPitchRemapper().collect_drum_pitches(track) == []


class TestCollectAllNotePitches:

    def test_includes_any_channel(self):
        track = [
            _Msg("note_on", 36, channel=0),
            _Msg("note_on", 38, channel=9),
            _Msg("note_off", 36, channel=0),
        ]

        assert DrumPitchRemapper().collect_all_note_pitches(track) == [36, 38]


class TestRemap:

    def test_returns_index_in_pitch_table(self):
        remapper = DrumPitchRemapper()
        table = [36, 38, 42]

        assert remapper.remap(36, table) == 0
        assert remapper.remap(38, table) == 1
        assert remapper.remap(42, table) == 2

    def test_raises_when_pitch_not_in_table(self):
        import pytest

        with pytest.raises(ValueError):
            DrumPitchRemapper().remap(99, [36, 38])
