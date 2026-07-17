# coding: utf-8

from dataclasses import dataclass

from howl_editor.ps1.formats.vag import format as fmt


@dataclass(frozen=True)
class VagStructureResult:
    """Structural verdict on a run of VAG bytes.

    A sample carved out of a bank blob is only correctly delimited if it lands
    on frame boundaries and ends where the encoder said it ends. When a slice
    is offset — because the size it was cut with disagrees with the bytes that
    are actually there — the flag byte lands on ADPCM payload instead of a
    frame header, which this catches."""

    frame_aligned: bool
    frame_count: int
    invalid_flag_frame: int | None
    terminates: bool

    @property
    def is_valid(self) -> bool:
        return (
            self.frame_aligned
            and self.frame_count > 0
            and self.invalid_flag_frame is None
            and self.terminates
        )


class VagStructureValidator:
    """Checks that raw VAG bytes are a well-formed ADPCM stream.

    Only structure is judged, never audio content: every frame's flag byte
    must be a legal combination, and the final frame must carry an end
    marker. Both hold for every stock CTR sample, so a failure means the
    bytes were cut at the wrong offset rather than that the audio is bad."""

    def validate(self, data: bytes) -> VagStructureResult:
        aligned = len(data) > 0 and len(data) % fmt.FRAME_SIZE == 0
        frames = len(data) // fmt.FRAME_SIZE

        if not aligned or frames == 0:
            return VagStructureResult(
                frame_aligned=aligned,
                frame_count=frames,
                invalid_flag_frame=None,
                terminates=False,
            )

        return VagStructureResult(
            frame_aligned=True,
            frame_count=frames,
            invalid_flag_frame=self._first_invalid_flag(data, frames),
            terminates=self._is_terminator(self._flags(data, frames - 1)),
        )

    def _flags(self, data: bytes, frame: int) -> int:
        return data[frame * fmt.FRAME_SIZE + 1]

    def _first_invalid_flag(self, data: bytes, frames: int) -> int | None:
        for i in range(frames):
            if self._flags(data, i) > fmt.FLAG_END_OF_DATA:
                return i

        return None

    def _is_terminator(self, flags: int) -> bool:
        """The encoder ends a sample either with the whole-byte sentinel or by
        setting Loop End — both mean the voice stops or jumps at this frame."""
        return flags == fmt.FLAG_END_OF_DATA or bool(flags & fmt.FLAG_LOOP_END)
