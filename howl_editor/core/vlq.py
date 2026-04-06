# coding: utf-8

_DATA_BITS = 7
_DATA_MASK = 0x7F
_CONTINUATION_BIT = 0x80


class VlqCodec:
    """Encodes and decodes variable-length quantities."""

    def read(self, data: bytes, pos: int) -> tuple[int, int]:
        """Read a variable-length quantity from data at pos.

        Returns (value, new_pos).
        Raises ValueError if data ends before VLQ is complete.
        """
        result = 0

        while pos < len(data):
            b = data[pos]
            pos += 1
            result = (result << _DATA_BITS) | (b & _DATA_MASK)

            if not (b & _CONTINUATION_BIT):
                return result, pos

        raise ValueError("Unterminated VLQ at end of data")

    def write(self, value: int) -> bytes:
        """Encode an integer as a variable-length quantity.

        Raises ValueError for negative values.
        """
        if value < 0:
            raise ValueError(f"VLQ value must be non-negative, got {value}")

        if value == 0:
            return b"\x00"

        parts: list[int] = []
        while value > 0:
            parts.append(value & _DATA_MASK)
            value >>= _DATA_BITS

        parts.reverse()
        out = bytearray()

        for i, p in enumerate(parts):
            if i < len(parts) - 1:
                out.append(p | _CONTINUATION_BIT)
            else:
                out.append(p)

        return bytes(out)
