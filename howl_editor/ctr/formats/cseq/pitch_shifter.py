# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from howl_editor.ctr.voice.pitch_stepper import PitchStepper


@dataclass(frozen=True)
class PitchShiftResult:
    """What a shift did, so the caller can report it without re-reading."""
    blob: bytes
    shifted: int
    clamped: int
    above_ceiling: int   # entries this shift pushed past the ceiling, not ones already there

    @property
    def is_clean(self) -> bool:
        return self.clamped == 0 and self.above_ceiling == 0


class CseqPitchShifter:
    """Moves stored base pitches by whole octaves — one descriptor, or every
    descriptor in a song at once, for the converted MIDI that came out a
    uniform octave off. Every shift reports what it did, since doubling a
    pitch can push notes past the SPU's ceiling."""

    def __init__(
        self, cseq_reader: CseqReader, cseq_writer: CseqWriter, pitch_stepper: PitchStepper,
    ):
        self._reader = cseq_reader
        self._writer = cseq_writer
        self._stepper = pitch_stepper

    def shift_instrument(self, song_data: bytes, inst_index: int, octaves: int) -> PitchShiftResult:
        return self.shift_instruments(song_data, [inst_index], octaves)

    def shift_percussion(self, song_data: bytes, perc_index: int, octaves: int) -> PitchShiftResult:
        return self.shift_percussions(song_data, [perc_index], octaves)

    def shift_instruments(
        self, song_data: bytes, inst_indices: list[int], octaves: int,
    ) -> PitchShiftResult:
        """Shift a selection of instruments as one edit."""
        cseq = self._reader.read(song_data)
        entries = self._pick(cseq.instruments, inst_indices, "Instrument")

        return self._apply(cseq, entries, octaves)

    def shift_percussions(
        self, song_data: bytes, perc_indices: list[int], octaves: int,
    ) -> PitchShiftResult:
        cseq = self._reader.read(song_data)
        entries = self._pick(cseq.percussions, perc_indices, "Percussion")

        return self._apply(cseq, entries, octaves)

    def _pick(self, table: list, indices: list[int], label: str) -> list:
        for index in indices:
            self._validate_index(index, len(table), label)

        return [table[i] for i in indices]

    def _apply(self, cseq, entries: list, octaves: int) -> PitchShiftResult:
        shifted = clamped = above = 0

        for entry in entries:
            old_pitch = entry.frequency
            new_pitch = self._stepper.octaves(old_pitch, octaves)
            entry.frequency = new_pitch

            if new_pitch != old_pitch:
                shifted += 1

            if new_pitch != self._exact_target(old_pitch, octaves):
                clamped += 1

            if self._crossed_ceiling(old_pitch, new_pitch):
                above += 1

        return PitchShiftResult(
            blob=self._writer.serialize(cseq),
            shifted=shifted,
            clamped=clamped,
            above_ceiling=above,
        )

    def _crossed_ceiling(self, old_pitch: int, new_pitch: int) -> bool:
        """Only a pitch this shift pushed over counts — one already above it
        would blame a downward shift for a problem it just made smaller."""
        return (
            self._stepper.exceeds_playable_ceiling(new_pitch)
            and not self._stepper.exceeds_playable_ceiling(old_pitch)
        )

    def _exact_target(self, old_pitch: int, octaves: int) -> int:
        """Where the shift would land with no field limits in the way."""
        return old_pitch << octaves if octaves >= 0 else old_pitch >> -octaves

    def _validate_index(self, index: int, length: int, label: str) -> None:
        if index < 0 or index >= length:
            raise IndexError(f"{label} index {index} out of range (0..{length - 1})")
