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
        both the intermediate and the final value are truncated to 16 bits."""
        idx = self._note_table_index(note_index, distort)
        freq = ((NOTE_FREQUENCY[idx] * base_pitch) >> 12) & 0xFFFF
        fine = distort & 0x3F

        if fine != 0:
            freq = (freq * (DISTORT_CONST_MUSIC[fine] + 0x100000)) >> 20

        return freq & 0xFFFF

    def instrument_register_untruncated(
        self, base_pitch: int, note_index: int, distort: int,
    ) -> int:
        """The pitch register a note *asks* for, before the SPU's 16-bit field
        truncates it.

        `instrument_register` returns what the console actually plays, so a
        note that overflows comes back already wrapped to a small, in-range
        value — which makes an overflow invisible to any 'is this over the
        ceiling?' check. This keeps the un-wrapped product so a caller can see
        that the note overflowed at all, and by how much."""
        idx = self._note_table_index(note_index, distort)
        freq = (NOTE_FREQUENCY[idx] * base_pitch) >> 12
        fine = distort & 0x3F

        if fine != 0:
            freq = (freq * (DISTORT_CONST_MUSIC[fine] + 0x100000)) >> 20

        return freq

    def _note_table_index(self, note_index: int, distort: int) -> int:
        """Resolve which noteFrequency[] entry a note lands on. The coarse half
        of the distort byte shifts the note; the result is clamped to the
        table, matching howl_InstrumentPitch."""
        note_offset = (distort >> 6) - 2
        return max(0, min(len(NOTE_FREQUENCY) - 1, note_index + note_offset))

    def instrument_plays_garbage(
        self, base_pitch: int, note_index: int, distort: int,
    ) -> bool:
        """Whether a note that overruns the pitch ceiling plays as garbage
        rather than merely flat."""
        if self.instrument_register_untruncated(base_pitch, note_index, distort) <= spu.MAX_PITCH:
            return False

        return self.instrument_register(base_pitch, note_index, distort) < spu.MAX_PITCH

    def _cap(self, register: int) -> int:
        """The register the SPU actually sounds: it will not decode a sample
        faster than 4.0×, so anything above MAX_PITCH plays at MAX_PITCH."""
        return min(spu.MAX_PITCH, register)

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
        """Instrument playback ratio — what the console actually sounds."""
        freq = self._cap(self.instrument_register(base_pitch, note_index, distort))

        return (freq / spu.FREQUENCY_UNIT) * (spu.SAMPLE_RATE / output_rate)

    def drum(
        self, drum_freq: int, distort: int, output_rate: int,
    ) -> float:
        """Drum playback ratio, capped at the SPU's 4.0× ceiling like any voice."""
        pitch = self._cap(self.drum_register(drum_freq, distort))

        return (pitch / spu.FREQUENCY_UNIT) * (spu.SAMPLE_RATE / output_rate)
