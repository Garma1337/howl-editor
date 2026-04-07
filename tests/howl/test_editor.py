# coding: utf-8

import pytest

from howl_editor.models import HowlFile


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


