# coding: utf-8

from collections.abc import Iterable
from dataclasses import dataclass

from howl_editor.ctr.audio_settings import DEFAULT_DISTORT
from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1 import spu


@dataclass(frozen=True)
class PitchHeadroom:
    """How a melodic instrument's base pitch fares against the notes it plays.

    Over the ceiling a note plays flat, or garbage if the register also wraps
    (see PitchCalculator)."""

    affected_notes: int
    highest_note: int | None
    garbage: bool

    @property
    def is_clean(self) -> bool:
        return self.affected_notes == 0


class PitchHeadroomInspector:
    """Checks a chosen base pitch against the notes an instrument will play,
    before anything is written — so the import dialog can warn that the top of
    a part will break in game rather than leaving it to be found by ear.

    This is the melodic counterpart to PitchCeilingValidator: the validator
    judges a finished CSEQ, this judges a base pitch a user is still choosing."""

    def __init__(self, pitch_calculator: PitchCalculator):
        self._pitch = pitch_calculator

    def inspect(self, base_pitch: int, notes: Iterable[int]) -> PitchHeadroom:
        affected = 0
        garbage = False
        highest: int | None = None

        for note in notes:
            if highest is None or note > highest:
                highest = note

            register = self._pitch.instrument_register_untruncated(
                base_pitch, note, DEFAULT_DISTORT,
            )
            if register > spu.MAX_PITCH:
                affected += 1
                if self._pitch.instrument_plays_garbage(base_pitch, note, DEFAULT_DISTORT):
                    garbage = True

        return PitchHeadroom(affected_notes=affected, highest_note=highest, garbage=garbage)

    def highest_safe_base_pitch(self, notes: Iterable[int]) -> int | None:
        """The largest base pitch at which every note stays under the 4.0×
        ceiling — the number that brings the instrument back into tune. None
        when there are no notes to constrain it.

        The register rises monotonically with the base pitch, so the highest
        note is the binding constraint and a binary search over the register
        range lands the exact threshold."""
        top: int | None = None
        for note in notes:
            if top is None or note > top:
                top = note

        if top is None:
            return None

        lo, hi, best = 0, cseq_fmt.MAX_PITCH_REGISTER, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            register = self._pitch.instrument_register_untruncated(mid, top, DEFAULT_DISTORT)

            if register <= spu.MAX_PITCH:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best
