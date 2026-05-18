# coding: utf-8

import pytest

from howl_editor.ctr.formats.cseq.track_mask_layout import TrackMaskLayout


@pytest.fixture
def track_mask_layout():
    return TrackMaskLayout()


class TestAppliesTo:

    def test_first_song(self, track_mask_layout):
        assert track_mask_layout.applies_to(0) is True

    def test_last_song(self, track_mask_layout):
        assert track_mask_layout.applies_to(27) is True

    def test_adventure_hub_included(self, track_mask_layout):
        # Adv Hub (26) has 20 sequences but seqs 0/1/2 still carry main/Aku/Uka.
        assert track_mask_layout.applies_to(26) is True

    def test_character_select_included(self, track_mask_layout):
        assert track_mask_layout.applies_to(27) is True

    def test_naughty_dog_crate_excluded(self, track_mask_layout):
        assert track_mask_layout.applies_to(28) is False

    def test_custom_song_excluded(self, track_mask_layout):
        assert track_mask_layout.applies_to(99) is False

    def test_negative_excluded(self, track_mask_layout):
        assert track_mask_layout.applies_to(-1) is False


class TestNaming:

    def test_main_sequence_name(self, track_mask_layout):
        assert track_mask_layout.name_for(0) == "Main music"

    def test_aku_sequence_name(self, track_mask_layout):
        assert track_mask_layout.name_for(1) == "Aku Aku mask"

    def test_uka_sequence_name(self, track_mask_layout):
        assert track_mask_layout.name_for(2) == "Uka Uka mask"

    def test_out_of_range_falls_back_to_index(self, track_mask_layout):
        assert track_mask_layout.name_for(5) == "Sequence 5"


class TestIcons:

    def test_each_slot_has_an_icon(self, track_mask_layout):
        for slot in track_mask_layout.mask_slots():
            assert track_mask_layout.icon_for(slot) != "•"

    def test_out_of_range_returns_fallback(self, track_mask_layout):
        assert track_mask_layout.icon_for(99) == "•"


class TestMaskSlots:

    def test_returns_three_indices(self, track_mask_layout):
        assert track_mask_layout.mask_slots() == (0, 1, 2)
