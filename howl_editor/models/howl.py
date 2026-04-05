# coding: utf-8

from dataclasses import dataclass, field

from howl_editor.constants import HWL_VERSION_RELEASE, SPU_ADDR_SIZE, OTHER_FX_SIZE, ENGINE_FX_SIZE


@dataclass
class SpuAddrEntry:
    ptr: int = 0
    size: int = 0

    @property
    def byte_size(self) -> int:
        return self.size * 8


@dataclass
class OtherFX:
    flags: int = 0
    volume: int = 0
    pitch: int = 0
    spu_index: int = 0
    duration: int = 0


@dataclass
class EngineFX:
    flags: int = 0
    volume: int = 0
    pitch: int = 0
    unk: int = 0
    spu_index: int = 0


@dataclass
class HowlHeader:
    """Parsed representation of the 40-byte HWL header."""
    magic: int = 0
    version: int = HWL_VERSION_RELEASE
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
    version: int = HWL_VERSION_RELEASE
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
            len(self.spu_addrs) * SPU_ADDR_SIZE
            + len(self.other_fx) * OTHER_FX_SIZE
            + len(self.engine_fx) * ENGINE_FX_SIZE
            + len(self.banks) * 2
            + len(self.songs) * 2
        )
