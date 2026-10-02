# coding: utf-8

import pytest

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.cseq.pitch_shifter import CseqPitchShifter
from howl_editor.ctr.voice.pitch_stepper import PitchStepper
from howl_editor.ps1 import spu
from tests.conftest import build_cseq_bytes

UNITY = 4096


@pytest.fixture
def shifter(cseq_reader, cseq_writer):
    return CseqPitchShifter(cseq_reader, cseq_writer, PitchStepper())


def _song(instruments=None, percussions=None) -> bytes:
    return build_cseq_bytes(instruments=instruments or [], percussions=percussions or [])


def _pitches(cseq_reader, blob) -> tuple[list[int], list[int]]:
    cseq = cseq_reader.read(blob)
    return [i.frequency for i in cseq.instruments], [p.frequency for p in cseq.percussions]


class TestShiftOneEntry:

    def test_instrument_up_an_octave(self, shifter, cseq_reader):
        blob = _song(instruments=[CseqInstrument(frequency=UNITY), CseqInstrument(frequency=800)])

        result = shifter.shift_instrument(blob, 0, 1)

        assert _pitches(cseq_reader, result.blob)[0] == [2 * UNITY, 800]
        assert (result.shifted, result.clamped) == (1, 0)

    def test_percussion_down_an_octave(self, shifter, cseq_reader):
        blob = _song(percussions=[CseqPercussion(frequency=UNITY)])

        result = shifter.shift_percussion(blob, 0, -1)

        assert _pitches(cseq_reader, result.blob)[1] == [UNITY // 2]

    def test_rejects_an_index_that_is_not_there(self, shifter):
        with pytest.raises(IndexError):
            shifter.shift_instrument(_song(instruments=[CseqInstrument()]), 3, 1)


class TestShiftWholeSong:

    def test_moves_instruments_and_percussion_together(self, shifter, cseq_reader):
        blob = _song(
            instruments=[CseqInstrument(frequency=UNITY), CseqInstrument(frequency=600)],
            percussions=[CseqPercussion(frequency=1000)],
        )

        result = shifter.shift_song(blob, -1)

        assert _pitches(cseq_reader, result.blob) == ([UNITY // 2, 300], [500])
        assert result.shifted == 3

    def test_reports_entries_pushed_past_the_playable_ceiling(self, shifter):
        blob = _song(instruments=[
            CseqInstrument(frequency=spu.MAX_PITCH // 2 + 1),   # crosses when doubled
            CseqInstrument(frequency=1000),                     # stays well under
        ])

        result = shifter.shift_song(blob, 1)

        assert result.above_ceiling == 1
        assert result.is_clean is False

    def test_reports_entries_the_field_could_not_take(self, shifter, cseq_reader):
        blob = _song(instruments=[CseqInstrument(frequency=cseq_fmt.MAX_PITCH_REGISTER)])

        result = shifter.shift_song(blob, 1)

        assert result.clamped == 1
        assert _pitches(cseq_reader, result.blob)[0] == [cseq_fmt.MAX_PITCH_REGISTER]

    def test_clean_when_everything_landed_where_it_was_asked(self, shifter):
        result = shifter.shift_song(_song(instruments=[CseqInstrument(frequency=1000)]), -1)

        assert result.is_clean is True

    def test_octave_down_then_up_restores_even_pitches(self, shifter, cseq_reader):
        blob = _song(instruments=[CseqInstrument(frequency=2000)])

        down = shifter.shift_song(blob, -1)
        back = shifter.shift_song(down.blob, 1)

        assert _pitches(cseq_reader, back.blob)[0] == [2000]
