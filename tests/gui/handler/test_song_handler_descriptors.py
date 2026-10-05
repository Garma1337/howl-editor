# coding: utf-8

"""Covers the pure helpers behind "add instrument / add percussion".

SongHandler is otherwise window-coupled (and the rest of it is untested by
convention), but these three are plain functions over a descriptor table, so
the behaviour that makes sample reuse discoverable is worth pinning down.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import CseqPercussion
from howl_editor.ctr.formats.cseq.pitch_shifter import PitchShiftResult
from howl_editor.gui.handler.song_handler import SongHandler


@pytest.fixture
def handler():
    # None stands in for the main window: these helpers never touch it.
    return SongHandler(None)


def _table(*sample_ids_and_freqs) -> list[CseqPercussion]:
    return [
        CseqPercussion(sample_id=sid, frequency=freq)
        for sid, freq in sample_ids_and_freqs
    ]


class TestDescriptorsUsing:

    def test_finds_every_descriptor_on_a_sample(self, handler):
        table = _table((447, 1024), (12, 4096), (447, 767))

        assert handler._descriptors_using(table, 447) == [0, 2]

    def test_empty_when_sample_unused(self, handler):
        assert handler._descriptors_using(_table((1, 100)), 999) == []

    def test_empty_table(self, handler):
        assert handler._descriptors_using([], 0) == []


class TestSeedPitch:

    def test_reuses_the_pitch_an_existing_descriptor_plays_it_at(self, handler):
        table = _table((12, 4096), (447, 1024))

        assert handler._seed_pitch_for(table, 447) == 1024

    def test_takes_the_first_match_when_several_pitches_exist(self, handler):
        table = _table((447, 1024), (447, 767))

        assert handler._seed_pitch_for(table, 447) == 1024

    def test_falls_back_to_default_for_an_unused_sample(self, handler):
        assert handler._seed_pitch_for(_table((1, 100)), 999) == cseq_fmt.DEFAULT_BASE_PITCH

    def test_falls_back_on_empty_table(self, handler):
        assert handler._seed_pitch_for([], 0) == cseq_fmt.DEFAULT_BASE_PITCH


class TestNewDescriptorBlurb:

    def test_plain_when_sample_is_unused(self, handler):
        blurb = handler._new_descriptor_blurb("percussion", 3, 447, [])

        assert blurb == "New percussion 3 → SPU #447"
        assert "shared" not in blurb

    def test_explains_sharing_when_sample_already_in_use(self, handler):
        blurb = handler._new_descriptor_blurb("percussion", 3, 447, [0, 2])

        assert "already used by percussion 0, 2" in blurb
        assert "shared, not duplicated" in blurb

    def test_names_the_descriptor_kind(self, handler):
        blurb = handler._new_descriptor_blurb("instrument", 1, 5, [0])

        assert "already used by instrument 0" in blurb

class TestShiftMessage:
    """The report after an octave shift — the only feedback the user gets that
    a transpose pushed something out of range."""

    def _result(self, shifted=3, clamped=0):
        return PitchShiftResult(blob=b"", shifted=shifted, clamped=clamped)

    def test_plain_count_when_everything_moved(self, handler):
        message = handler._shift_message(self._result(), "up", 14)

        assert "3 pitch(es) up an octave in song 14" in message
        assert "ceiling" not in message

    def test_mentions_pitches_held_at_the_ceiling(self, handler):
        message = handler._shift_message(self._result(clamped=2), "up", 0)

        assert "2 held" in message and "4.0" in message

    def test_explains_a_shift_that_moved_nothing(self, handler):
        message = handler._nothing_moved_message(self._result(shifted=0, clamped=1), "up", 7)

        assert "4.0" in message and "song 7" in message

    def test_a_shift_with_nothing_to_move_says_so_plainly(self, handler):
        message = handler._nothing_moved_message(self._result(shifted=0), "down", 7)

        assert "Nothing to shift down in song 7" in message

