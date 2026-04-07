# coding: utf-8

from howl_editor.audio.settings.ctr import (
    NOTE_FREQUENCY, DISTORT_CONST_MUSIC, DISTORT_CONST_OTHER_FX, DEFAULT_DISTORT,
)
from howl_editor.audio.settings.ps1 import PS1_SAMPLE_RATE, PS1_FREQUENCY_UNIT


class PitchCalculator:
    """Computes somewhat CTR-accurate pitch ratios for instruments and drums.

    Tries to match DECOMP_howl_InstrumentPitch (h30) and the drum pitch logic
    in h41_howl_InitChannelAttr_Music.
    """

    def instrument(
        self, base_pitch: int, note_index: int, distort: int, output_rate: int,
    ) -> float:
        """Calculate instrument pitch ratio from base pitch, note, and distortion."""
        note_offset = (distort >> 6) - 2
        idx = max(0, min(len(NOTE_FREQUENCY) - 1, note_index + note_offset))
        freq = (NOTE_FREQUENCY[idx] * base_pitch) >> 12
        freq &= 0xFFFF
        fine = distort & 0x3F

        if fine != 0:
            freq = (freq * (DISTORT_CONST_MUSIC[fine] + 0x100000)) >> 20

        return (freq / PS1_FREQUENCY_UNIT) * (PS1_SAMPLE_RATE / output_rate)

    def drum(
        self, drum_freq: int, distort: int, output_rate: int,
    ) -> float:
        """Calculate drum pitch ratio with optional distortion."""
        if distort == DEFAULT_DISTORT:
            pitch = drum_freq
        else:
            pitch = (drum_freq * DISTORT_CONST_OTHER_FX[distort]) >> 16

        return (pitch / PS1_FREQUENCY_UNIT) * (PS1_SAMPLE_RATE / output_rate)
