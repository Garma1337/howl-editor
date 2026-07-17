# coding: utf-8

from howl_editor.ctr.audio_settings import (
    NOTE_FREQUENCY, DISTORT_CONST_MUSIC, DISTORT_CONST_OTHER_FX, DEFAULT_DISTORT,
)
from howl_editor.ps1 import spu


class PitchCalculator:
    """Computes somewhat CTR-accurate pitch ratios for instruments and drums.

    Tries to match DECOMP_howl_InstrumentPitch (h30) and the drum pitch logic
    in h41_howl_InitChannelAttr_Music.
    """

    def instrument_register(
        self, base_pitch: int, note_index: int, distort: int,
    ) -> int:
        """The raw SPU pitch register a note resolves to.

        Mirrors howl_InstrumentPitch: the note table scales the base pitch, and
        both the intermediate and the final value are truncated to 16 bits.
        Callers wanting a playback ratio should use `instrument`; this is for
        checking the value the console would actually be handed."""
        note_offset = (distort >> 6) - 2
        idx = max(0, min(len(NOTE_FREQUENCY) - 1, note_index + note_offset))
        freq = ((NOTE_FREQUENCY[idx] * base_pitch) >> 12) & 0xFFFF
        fine = distort & 0x3F

        if fine != 0:
            freq = (freq * (DISTORT_CONST_MUSIC[fine] + 0x100000)) >> 20

        return freq & 0xFFFF

    def drum_register(self, drum_freq: int, distort: int) -> int:
        """The raw SPU pitch register a percussion hit resolves to. The note
        number picks *which* percussion, so unlike an instrument nothing
        transposes this — the stored pitch is played as-is, give or take a bend."""
        if distort == DEFAULT_DISTORT:
            return drum_freq

        return (drum_freq * DISTORT_CONST_OTHER_FX[distort]) >> 16

    def instrument(
        self, base_pitch: int, note_index: int, distort: int, output_rate: int,
    ) -> float:
        """Calculate instrument pitch ratio from base pitch, note, and distortion."""
        freq = self.instrument_register(base_pitch, note_index, distort)

        return (freq / spu.FREQUENCY_UNIT) * (spu.SAMPLE_RATE / output_rate)

    def drum(
        self, drum_freq: int, distort: int, output_rate: int,
    ) -> float:
        """Calculate drum pitch ratio with optional distortion."""
        pitch = self.drum_register(drum_freq, distort)

        return (pitch / spu.FREQUENCY_UNIT) * (spu.SAMPLE_RATE / output_rate)
