# coding: utf-8


class CseqSizeValidator:
    """Checks a serialized CSEQ against the game's hard size ceiling.

    Crash Team Racing's CSEQ loader reads up to 11 disc sectors (0x5800 bytes)
    per song. Anything beyond that won't load in-game, even though the file is
    technically well-formed.
    """

    MAX_CSEQ_BYTES = 0x5800

    def is_within_limit(self, data: bytes) -> bool:
        return len(data) <= self.MAX_CSEQ_BYTES

    def calculate_overflow_bytes(self, data: bytes) -> int:
        return max(0, len(data) - self.MAX_CSEQ_BYTES)
