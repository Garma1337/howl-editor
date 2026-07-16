# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr import constants
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator


@dataclass(frozen=True)
class CseqSizeCheck:
    within_limit: bool
    size: int
    limit: int
    overflow: int
    warning_text: str


class CseqSizeGuard:
    """Checks a serialized CSEQ against the engine's fixed song buffer and
    produces the warning a mutation path shows before writing an oversized song.

    The console reads a song into an 0x5800-byte buffer with no bounds check,
    so an oversized song silently overruns adjacent memory.
    """

    def __init__(self, validator: CseqSizeValidator):
        self._validator = validator

    def check(self, cseq_blob: bytes) -> CseqSizeCheck:
        size = len(cseq_blob)
        within = self._validator.is_within_limit(cseq_blob)
        overflow = self._validator.calculate_overflow_bytes(cseq_blob)

        text = "" if within else (
            f"This sequence is {size} bytes — {overflow} over the "
            f"{constants.MAX_CSEQ_BYTES}-byte (0x5800) limit the game reserves for "
            f"one song. The console loads songs into a fixed buffer with no size "
            f"check, so an oversized song overruns it and causes crashes or broken "
            f"audio in game. Shorten the song, remove tracks, or reduce event "
            f"density.\n\nSave it anyway?"
        )

        return CseqSizeCheck(
            within_limit=within,
            size=size,
            limit=constants.MAX_CSEQ_BYTES,
            overflow=overflow,
            warning_text=text,
        )
