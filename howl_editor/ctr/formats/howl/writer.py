# coding: utf-8

from dataclasses import dataclass, field
from pathlib import Path
from struct import pack_into

from howl_editor.ctr.formats.howl.models import HowlFile, HowlHeader, SpuAddrEntry, OtherFX, EngineFX
from howl_editor.ps1.constants import SECTOR_SIZE, bytes_to_sectors


@dataclass
class HowlLayout:
    """Pre-computed sector layout for serialization."""
    header_sectors: int = 0
    bank_offsets: list[int] = field(default_factory=list)
    song_offsets: list[int] = field(default_factory=list)
    total_sectors: int = 0


class HowlWriter:

    def serialize(self, hwl: HowlFile) -> bytes:
        """Serialize a HowlFile to raw bytes."""
        layout = self._calculate_layout(hwl)
        buf = self._allocate_buffer(layout)

        self._write_header(buf, hwl)
        pos = HowlHeader.SIZE
        pos = self._write_spu_addrs(buf, pos, hwl)
        pos = self._write_other_fx(buf, pos, hwl)
        pos = self._write_engine_fx(buf, pos, hwl)
        pos = self._write_offset_table(buf, pos, layout.bank_offsets)
        pos = self._write_offset_table(buf, pos, layout.song_offsets)
        self._write_blobs(buf, hwl.banks, layout.bank_offsets)
        self._write_blobs(buf, hwl.songs, layout.song_offsets)

        return bytes(buf)

    def write_file(self, hwl: HowlFile, path: str | Path) -> None:
        """Serialize and write to disk."""
        Path(path).write_bytes(self.serialize(hwl))

    def _calculate_layout(self, hwl: HowlFile) -> HowlLayout:
        header_bytes = HowlHeader.SIZE + hwl.header_data_size
        header_sectors = bytes_to_sectors(header_bytes)
        current = header_sectors

        bank_offsets = []
        for bank in hwl.banks:
            bank_offsets.append(current)
            current += bytes_to_sectors(len(bank))

        song_offsets = []
        for song in hwl.songs:
            song_offsets.append(current)
            current += bytes_to_sectors(len(song))

        return HowlLayout(
            header_sectors=header_sectors,
            bank_offsets=bank_offsets,
            song_offsets=song_offsets,
            total_sectors=current,
        )

    def _allocate_buffer(self, layout: HowlLayout) -> bytearray:
        return bytearray(layout.total_sectors * SECTOR_SIZE)

    def _write_header(self, buf: bytearray, hwl: HowlFile) -> None:
        HowlHeader.STRUCT.pack_into(
            buf, 0,
            HowlHeader.MAGIC, hwl.version, hwl.reserved1, hwl.reserved2,
            len(hwl.spu_addrs), len(hwl.other_fx), len(hwl.engine_fx),
            len(hwl.banks), len(hwl.songs), hwl.header_data_size,
        )

    def _write_spu_addrs(self, buf: bytearray, pos: int, hwl: HowlFile) -> int:
        for entry in hwl.spu_addrs:
            SpuAddrEntry.STRUCT.pack_into(buf, pos, entry.ptr, entry.size)
            pos += SpuAddrEntry.SIZE

        return pos

    def _write_other_fx(self, buf: bytearray, pos: int, hwl: HowlFile) -> int:
        for fx in hwl.other_fx:
            OtherFX.STRUCT.pack_into(buf, pos, fx.flags, fx.volume, fx.pitch, fx.spu_index, fx.duration)
            pos += OtherFX.SIZE
        
        return pos

    def _write_engine_fx(self, buf: bytearray, pos: int, hwl: HowlFile) -> int:
        for fx in hwl.engine_fx:
            EngineFX.STRUCT.pack_into(buf, pos, fx.flags, fx.volume, fx.pitch, fx.unk, fx.spu_index)
            pos += EngineFX.SIZE
        
        return pos

    def _write_offset_table(self, buf: bytearray, pos: int, offsets: list[int]) -> int:
        for offset in offsets:
            pack_into("<H", buf, pos, offset)
            pos += 2
        
        return pos

    def _write_blobs(self, buf: bytearray, blobs: list[bytes], offsets: list[int]) -> None:
        for blob, offset in zip(blobs, offsets):
            start = offset * SECTOR_SIZE
            buf[start:start + len(blob)] = blob
