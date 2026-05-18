# coding: utf-8

from howl_editor.midi.drum_name_resolver import DrumNameResolver


class TestGetLabel:

    def test_known_drum_pitches(self):
        names = DrumNameResolver()

        assert names.get_label(36) == "Kick"
        assert names.get_label(38) == "Snare"
        assert names.get_label(42) == "Closed Hi-Hat"

    def test_unknown_pitch_falls_back_to_note_number(self):
        assert DrumNameResolver().get_label(200) == "Note 200"
