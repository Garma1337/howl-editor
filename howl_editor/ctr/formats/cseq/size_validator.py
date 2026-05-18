# coding: utf-8

from howl_editor.ctr import constants


class CseqSizeValidator:
    """Checks a serialized CSEQ against the game's hard size ceiling."""

    def is_within_limit(self, data: bytes) -> bool:
        return len(data) <= constants.MAX_CSEQ_BYTES

    def calculate_overflow_bytes(self, data: bytes) -> int:
        return max(0, len(data) - constants.MAX_CSEQ_BYTES)
