# coding: utf-8

from dataclasses import dataclass, field
from struct import Struct


@dataclass
class SpuAddrEntry:
    STRUCT = Struct("<HH")
    SIZE = STRUCT.size

    ptr: int = 0
    size: int = 0

    @property
    def byte_size(self) -> int:
        return self.size * 8


@dataclass
class OtherFX:
    STRUCT = Struct("<BBHHH")
    SIZE = STRUCT.size

    flags: int = 0
    volume: int = 0
    pitch: int = 0
    spu_index: int = 0
    duration: int = 0


@dataclass
class EngineFX:
    STRUCT = Struct("<BBHHH")
    SIZE = STRUCT.size

    flags: int = 0
    volume: int = 0
    pitch: int = 0
    unk: int = 0
    spu_index: int = 0


@dataclass
class HowlHeader:
    """Parsed representation of the 40-byte HWL header."""
    MAGIC = 0x4C574F48  # "HOWL" little-endian
    VERSION_RELEASE = 0x80
    STRUCT = Struct("<IIIIIIIIII")
    SIZE = STRUCT.size

    magic: int = 0
    version: int = VERSION_RELEASE
    reserved1: int = 0
    reserved2: int = 0
    num_spu: int = 0
    num_other: int = 0
    num_engine: int = 0
    num_banks: int = 0
    num_songs: int = 0
    header_data_size: int = 0


@dataclass
class HowlFile:
    version: int = HowlHeader.VERSION_RELEASE
    reserved1: int = 0
    reserved2: int = 0
    spu_addrs: list[SpuAddrEntry] = field(default_factory=list)
    other_fx: list[OtherFX] = field(default_factory=list)
    engine_fx: list[EngineFX] = field(default_factory=list)
    banks: list[bytes] = field(default_factory=list)
    songs: list[bytes] = field(default_factory=list)

    @property
    def header_data_size(self) -> int:
        """Size of all metadata tables after the fixed header."""
        return (
            len(self.spu_addrs) * SpuAddrEntry.SIZE
            + len(self.other_fx) * OtherFX.SIZE
            + len(self.engine_fx) * EngineFX.SIZE
            + len(self.banks) * 2
            + len(self.songs) * 2
        )
