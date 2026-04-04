# coding: utf-8

from struct import Struct

# Sector alignment
SECTOR_SIZE = 0x800

# HWL header
HWL_MAGIC = 0x4C574F48  # "HOWL" little-endian
HWL_VERSION_RELEASE = 0x80

HEADER_STRUCT = Struct("<IIIIIIIIII")
HEADER_SIZE = HEADER_STRUCT.size  # 40 bytes

SPU_ADDR_STRUCT = Struct("<HH")
SPU_ADDR_SIZE = SPU_ADDR_STRUCT.size  # 4 bytes

OTHER_FX_STRUCT = Struct("<BBHHH")
OTHER_FX_SIZE = OTHER_FX_STRUCT.size  # 8 bytes

ENGINE_FX_STRUCT = Struct("<BBHHH")
ENGINE_FX_SIZE = ENGINE_FX_STRUCT.size  # 8 bytes

# VAG format
VAG_MAGIC = b"VAGp"
VAG_HEADER_SIZE = 48
VAG_HEADER_STRUCT = Struct(">4sIIII")  # magic, version, reserved, data_size, sample_rate

# CSEQ header
CSEQ_HEADER_STRUCT = Struct("<IBBh")
CSEQ_HEADER_SIZE = CSEQ_HEADER_STRUCT.size  # 8 bytes

CSEQ_INSTRUMENT_STRUCT = Struct("<BBhHHI")
CSEQ_INSTRUMENT_SIZE = CSEQ_INSTRUMENT_STRUCT.size  # 12 bytes

CSEQ_PERCUSSION_STRUCT = Struct("<BBHHh")
CSEQ_PERCUSSION_SIZE = CSEQ_PERCUSSION_STRUCT.size  # 8 bytes


def bytes_to_sectors(n: int) -> int:
    """Round up byte count to sector count."""
    return (n + SECTOR_SIZE - 1) // SECTOR_SIZE
