# coding: utf-8

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ps1 import spu

SEMITONES_PER_OCTAVE = 12


class PitchStepper:
    """Moves a base pitch by musical intervals instead of raw register counts.

    The pitch register is a speed multiplier (4096 = 1.0×), so an octave is a
    doubling and a semitone is a factor of 2^(1/12). Editing it as a number
    means doing that arithmetic by hand, which is what makes 'put this
    instrument an octave down' awkward."""

    def octaves(self, register: int, octaves: int) -> int:
        """Shift by whole octaves. Exact: an octave up then down round-trips."""
        return self._clamp(register, self._doubled(register, octaves), octaves)

    def semitones(self, register: int, semitones: int) -> int:
        """Shift by semitones. Whole octaves stay exact; other intervals are
        rounded to the nearest register value, so repeated small steps drift
        slightly — stepping by octaves does not."""
        octaves, remainder = divmod(semitones, SEMITONES_PER_OCTAVE)
        shifted = self._doubled(register, octaves)

        if remainder:
            shifted = round(shifted * 2 ** (remainder / SEMITONES_PER_OCTAVE))

        return self._clamp(register, shifted, semitones)

    def exceeds_playable_ceiling(self, register: int) -> bool:
        """Above this the SPU plays the sample flat, at its 4.0× ceiling."""
        return register > spu.MAX_PITCH

    def _doubled(self, register: int, octaves: int) -> int:
        return register << octaves if octaves >= 0 else register >> -octaves

    def _clamp(self, register: int, shifted: int, direction: int) -> int:
        """Hold the result inside the field, keep a sounding pitch off 0 (where
        the sample stops advancing), and never let a step cross back past its
        starting point — on a tiny register that floor would otherwise bounce a
        downward step above the original."""
        floor = 1 if register > 0 else 0
        result = max(floor, min(cseq_fmt.MAX_PITCH_REGISTER, shifted))

        if direction < 0:
            return min(result, register)

        if direction > 0:
            return max(result, register)

        return result
