# coding: utf-8

def read_vlq(data: bytes, pos: int) -> tuple[int, int]:
    """
    Read a variable-length quantity from data at pos.
    Returns (value, new_pos).
    Raises ValueError if data ends before VLQ is complete.
    """
    result = 0

    while pos < len(data):
        b = data[pos]
        pos += 1
        result = (result << 7) | (b & 0x7F)
    
        if not (b & 0x80):
            return result, pos
    
    raise ValueError(f"Unterminated VLQ at end of data")


def write_vlq(value: int) -> bytes:
    """
    Encode an integer as a variable-length quantity.
    Raises ValueError for negative values.
    """
    if value < 0:
        raise ValueError(f"VLQ value must be non-negative, got {value}")

    if value == 0:
        return b"\x00"
    
    parts: list[int] = []
    while value > 0:
        parts.append(value & 0x7F)
        value >>= 7
    
    parts.reverse()
    out = bytearray()
    
    for i, p in enumerate(parts):
        if i < len(parts) - 1:
            out.append(p | 0x80)
        else:
            out.append(p)
    
    return bytes(out)
