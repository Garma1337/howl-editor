# coding: utf-8

import pytest

from howl_editor.models import HowlFile, OtherFX


class TestAddBank:

    def test_adds_bank(self, howl_editor):
        hwl = HowlFile()
        idx = howl_editor.add_bank(hwl, b"\x01\x02")

        assert idx == 0
        assert hwl.banks[0] == b"\x01\x02"

    def test_returns_sequential_indices(self, howl_editor):
        hwl = HowlFile()

        assert howl_editor.add_bank(hwl, b"a") == 0
        assert howl_editor.add_bank(hwl, b"b") == 1
        assert howl_editor.add_bank(hwl, b"c") == 2


class TestRemoveBank:

    def test_removes_bank(self, howl_editor):
        hwl = HowlFile(banks=[b"a", b"b", b"c"])
        howl_editor.remove_bank(hwl, 1)

        assert hwl.banks == [b"a", b"c"]

    def test_out_of_range_raises(self, howl_editor):
        hwl = HowlFile(banks=[b"a"])

        with pytest.raises(IndexError, match="Bank"):
            howl_editor.remove_bank(hwl, 5)

    def test_negative_index_raises(self, howl_editor):
        hwl = HowlFile(banks=[b"a"])

        with pytest.raises(IndexError):
            howl_editor.remove_bank(hwl, -1)

    def test_empty_list_raises(self, howl_editor):
        hwl = HowlFile()

        with pytest.raises(IndexError):
            howl_editor.remove_bank(hwl, 0)


class TestReplaceBank:

    def test_replaces_bank(self, howl_editor):
        hwl = HowlFile(banks=[b"old"])
        howl_editor.replace_bank(hwl, 0, b"new")

        assert hwl.banks[0] == b"new"

    def test_out_of_range_raises(self, howl_editor):
        hwl = HowlFile(banks=[b"a"])

        with pytest.raises(IndexError):
            howl_editor.replace_bank(hwl, 3, b"new")


class TestAddSong:

    def test_adds_song(self, howl_editor):
        hwl = HowlFile()
        idx = howl_editor.add_song(hwl, b"\xCC")

        assert idx == 0
        assert hwl.songs[0] == b"\xCC"


class TestRemoveSong:

    def test_removes_song(self, howl_editor):
        hwl = HowlFile(songs=[b"x", b"y"])
        howl_editor.remove_song(hwl, 0)

        assert hwl.songs == [b"y"]

    def test_out_of_range_raises(self, howl_editor):
        hwl = HowlFile()

        with pytest.raises(IndexError, match="Song"):
            howl_editor.remove_song(hwl, 0)


class TestReplaceSong:

    def test_replaces_song(self, howl_editor):
        hwl = HowlFile(songs=[b"old"])
        howl_editor.replace_song(hwl, 0, b"new")

        assert hwl.songs[0] == b"new"


class TestMoveBank:

    def test_moves_forward(self, howl_editor):
        hwl = HowlFile(banks=[b"a", b"b", b"c"])
        howl_editor.move_bank(hwl, 0, 2)

        assert hwl.banks == [b"b", b"c", b"a"]

    def test_moves_backward(self, howl_editor):
        hwl = HowlFile(banks=[b"a", b"b", b"c"])
        howl_editor.move_bank(hwl, 2, 0)

        assert hwl.banks == [b"c", b"a", b"b"]

    def test_same_position_is_noop(self, howl_editor):
        hwl = HowlFile(banks=[b"a", b"b", b"c"])
        howl_editor.move_bank(hwl, 1, 1)

        assert hwl.banks == [b"a", b"b", b"c"]

    def test_out_of_range_raises(self, howl_editor):
        hwl = HowlFile(banks=[b"a"])

        with pytest.raises(IndexError):
            howl_editor.move_bank(hwl, 0, 5)

    def test_negative_index_raises(self, howl_editor):
        hwl = HowlFile(banks=[b"a", b"b"])

        with pytest.raises(IndexError):
            howl_editor.move_bank(hwl, -1, 0)


class TestMoveSong:

    def test_moves_forward(self, howl_editor):
        hwl = HowlFile(songs=[b"x", b"y", b"z"])
        howl_editor.move_song(hwl, 0, 2)

        assert hwl.songs == [b"y", b"z", b"x"]

    def test_moves_backward(self, howl_editor):
        hwl = HowlFile(songs=[b"x", b"y", b"z"])
        howl_editor.move_song(hwl, 2, 0)

        assert hwl.songs == [b"z", b"x", b"y"]

    def test_out_of_range_raises(self, howl_editor):
        hwl = HowlFile(songs=[b"x"])

        with pytest.raises(IndexError):
            howl_editor.move_song(hwl, 0, 3)


class TestSetSampleRate:

    def test_updates_matching_other_fx_pitch(self, howl_editor):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=7, pitch=0)])

        touched = howl_editor.set_sample_rate(hwl, 7, 44100)

        assert touched == 1
        assert hwl.other_fx[0].pitch == 4096

    def test_updates_every_matching_entry(self, howl_editor):
        hwl = HowlFile(other_fx=[
            OtherFX(spu_index=7, pitch=0),
            OtherFX(spu_index=8, pitch=0),
            OtherFX(spu_index=7, pitch=0),
        ])

        touched = howl_editor.set_sample_rate(hwl, 7, 22050)

        assert touched == 2
        assert hwl.other_fx[0].pitch == 2048
        assert hwl.other_fx[1].pitch == 0  # untouched — different spu_index
        assert hwl.other_fx[2].pitch == 2048

    def test_returns_zero_when_no_match(self, howl_editor):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=99, pitch=4096)])

        touched = howl_editor.set_sample_rate(hwl, 7, 44100)

        assert touched == 0
        assert hwl.other_fx[0].pitch == 4096  # unrelated entry untouched

    def test_does_not_create_entries(self, howl_editor):
        hwl = HowlFile()

        howl_editor.set_sample_rate(hwl, 7, 44100)

        assert hwl.other_fx == []

    def test_zero_or_negative_rate_is_noop(self, howl_editor):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=7, pitch=4096)])

        assert howl_editor.set_sample_rate(hwl, 7, 0) == 0
        assert howl_editor.set_sample_rate(hwl, 7, -100) == 0
        assert hwl.other_fx[0].pitch == 4096

    def test_rounds_to_nearest_pitch_unit(self, howl_editor):
        # 11025 Hz → 11025/44100 * 4096 = 1024 exactly
        hwl = HowlFile(other_fx=[OtherFX(spu_index=0, pitch=0)])

        howl_editor.set_sample_rate(hwl, 0, 11025)

        assert hwl.other_fx[0].pitch == 1024


class TestAttachSampleRate:

    def test_updates_existing_entry(self, howl_editor):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=7, pitch=0)])

        howl_editor.attach_sample_rate(hwl, 7, 44100)

        assert len(hwl.other_fx) == 1
        assert hwl.other_fx[0].pitch == 4096

    def test_creates_entry_when_none_match(self, howl_editor):
        hwl = HowlFile()

        howl_editor.attach_sample_rate(hwl, 12, 22050)

        assert len(hwl.other_fx) == 1
        created = hwl.other_fx[0]
        assert created.spu_index == 12
        assert created.pitch == 2048
        assert created.volume == 255

    def test_creates_entry_even_when_other_unrelated_fx_exist(self, howl_editor):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=99, pitch=4096)])

        howl_editor.attach_sample_rate(hwl, 12, 44100)

        assert len(hwl.other_fx) == 2
        assert hwl.other_fx[0].spu_index == 99       # pre-existing untouched
        assert hwl.other_fx[1].spu_index == 12       # newly created
        assert hwl.other_fx[1].pitch == 4096

    def test_does_not_create_when_zero_rate(self, howl_editor):
        hwl = HowlFile()

        howl_editor.attach_sample_rate(hwl, 7, 0)

        assert hwl.other_fx == []

    def test_does_not_create_duplicate_when_entry_already_matches(self, howl_editor):
        hwl = HowlFile(other_fx=[
            OtherFX(spu_index=7, pitch=0),
            OtherFX(spu_index=7, pitch=0),
        ])

        howl_editor.attach_sample_rate(hwl, 7, 44100)

        # Both existing entries updated, none appended.
        assert len(hwl.other_fx) == 2
        assert all(fx.pitch == 4096 for fx in hwl.other_fx)

