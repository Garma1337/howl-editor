# coding: utf-8

import pytest

from howl_editor.ctr.audio_settings import DEFAULT_DISTORT, NOTE_FREQUENCY
from howl_editor.ctr.diagnostics.pitch_ceiling_validator import PitchCeilingValidator
from howl_editor.ctr.formats.cseq.models import (
    CseqEvent, CseqEventType, CseqFile, CseqInstrument, CseqPercussion, CseqSong,
    CseqTrack,
)
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1 import spu


@pytest.fixture
def validator():
    return PitchCeilingValidator(PitchCalculator())


def _melodic(patch: int, notes: list[int], bend: int | None = None) -> CseqTrack:
    events = [CseqEvent(event_type=CseqEventType.CHANGE_PATCH, pitch=patch)]

    if bend is not None:
        events.append(CseqEvent(event_type=CseqEventType.PITCH_BEND, pitch=bend))

    for n in notes:
        events.append(CseqEvent(event_type=CseqEventType.NOTE_ON, pitch=n, velocity=100))

    events.append(CseqEvent(event_type=CseqEventType.END_TRACK))

    return CseqTrack(flags=0, events=events)


def _cseq(instruments, tracks, percussions=None) -> CseqFile:
    return CseqFile(
        instruments=instruments,
        percussions=percussions or [],
        songs=[CseqSong(bpm=120, tpqn=480, tracks=tracks)],
    )


class TestWithinCeiling:
    """Notes the SPU can actually reach must stay silent — every stock song
    sits about an octave below the ceiling, so a noisy check would be useless."""

    def test_unity_base_pitch_at_middle_c_passes(self, validator):
        # NOTE_FREQUENCY[60] is unity, so the register is just the base pitch.
        cseq = _cseq([CseqInstrument(sample_id=0, frequency=4096)], [_melodic(0, [60])])

        assert validator.validate(cseq).is_valid

    def test_low_base_pitch_can_never_overflow(self, validator):
        # At 1024 the note table tops out before the register can saturate.
        top = len(NOTE_FREQUENCY) - 1
        cseq = _cseq([CseqInstrument(sample_id=0, frequency=1024)], [_melodic(0, [top])])

        assert validator.validate(cseq).is_valid

    def test_notes_the_song_never_plays_are_not_judged(self, validator):
        """An instrument may be tuned so that unreachable notes would overflow;
        only what the song actually triggers matters."""
        cseq = _cseq([CseqInstrument(sample_id=0, frequency=4096)], [_melodic(0, [60, 62])])

        assert validator.validate(cseq).is_valid


class TestOverCeiling:

    def test_high_note_on_a_raised_base_pitch_is_flagged(self, validator):
        # base 4096 -> NOTE_FREQUENCY[84] is 0x4000, so the register lands on
        # 16384, one past the ceiling.
        cseq = _cseq([CseqInstrument(sample_id=7, frequency=4096)], [_melodic(0, [84])])
        result = validator.validate(cseq)

        assert not result.is_valid
        item = result.exceedances[0]
        assert item.note == 84
        assert item.register == spu.MAX_PITCH + 1
        assert item.over_by == 1
        assert item.sample_id == 7
        assert item.is_drum is False

    def test_reports_the_lowest_offending_note_only(self, validator):
        """Everything above the first bad note overflows too — the user needs
        the threshold, not a list."""
        cseq = _cseq([CseqInstrument(sample_id=0, frequency=4096)], [_melodic(0, [90, 84, 87])])
        result = validator.validate(cseq)

        assert len(result.exceedances) == 1
        assert result.exceedances[0].note == 84

    def test_same_sample_is_fine_at_a_lower_base_pitch(self, validator):
        """The fix the check exists to point at: halve the base pitch and the
        same note comes back under."""
        over = _cseq([CseqInstrument(sample_id=0, frequency=4096)], [_melodic(0, [84])])
        under = _cseq([CseqInstrument(sample_id=0, frequency=2048)], [_melodic(0, [84])])

        assert not validator.validate(over).is_valid
        assert validator.validate(under).is_valid

    def test_each_instrument_reported_separately(self, validator):
        cseq = _cseq(
            [
                CseqInstrument(sample_id=1, frequency=4096),
                CseqInstrument(sample_id=2, frequency=4096),
            ],
            [_melodic(0, [84]), _melodic(1, [86])],
        )

        assert {e.slot for e in validator.validate(cseq).exceedances} == {0, 1}

    def test_worst_picks_the_highest_register(self, validator):
        cseq = _cseq(
            [
                CseqInstrument(sample_id=1, frequency=4096),
                CseqInstrument(sample_id=2, frequency=8192),
            ],
            [_melodic(0, [84]), _melodic(1, [84])],
        )
        worst = validator.validate(cseq).worst

        assert worst.slot == 1


class TestPercussion:
    """A drum's note number picks which percussion rather than transposing it,
    so its stored pitch is what reaches the register."""

    def test_percussion_over_the_ceiling_is_flagged(self, validator):
        cseq = _cseq(
            [], [], percussions=[CseqPercussion(sample_id=3, frequency=spu.MAX_PITCH + 100)],
        )
        result = validator.validate(cseq)

        assert not result.is_valid
        item = result.exceedances[0]
        assert item.is_drum is True
        assert item.note is None
        assert item.slot == 0
        assert item.over_by == 100

    def test_percussion_at_the_ceiling_passes(self, validator):
        cseq = _cseq([], [], percussions=[CseqPercussion(sample_id=3, frequency=spu.MAX_PITCH)])

        assert validator.validate(cseq).is_valid


class TestBoundary:

    def test_exactly_at_the_ceiling_is_allowed(self, validator):
        pitch = PitchCalculator()
        # Find a base pitch whose register at note 60 is exactly the ceiling.
        cseq = _cseq(
            [CseqInstrument(sample_id=0, frequency=spu.MAX_PITCH)], [_melodic(0, [60])],
        )

        assert pitch.instrument_register(spu.MAX_PITCH, 60, DEFAULT_DISTORT) == spu.MAX_PITCH
        assert validator.validate(cseq).is_valid

    def test_one_past_the_ceiling_is_flagged(self, validator):
        cseq = _cseq(
            [CseqInstrument(sample_id=0, frequency=spu.MAX_PITCH + 1)], [_melodic(0, [60])],
        )

        assert not validator.validate(cseq).is_valid
