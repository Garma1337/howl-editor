# coding: utf-8

from pathlib import Path
from struct import unpack_from

from howl_editor.models import HowlFile, HowlHeader, SpuAddrEntry, OtherFX, EngineFX
from howl_editor.models.howl import SECTOR_SIZE, bytes_to_sectors


class HowlReader:

    def read(self, data: bytes) -> HowlFile:
        """Parse raw HWL bytes into a HowlFile."""
        self._validate_min_size(data)
        header = self._parse_header(data)
        self._validate_magic(header)
        pos = HowlHeader.SIZE

        spu_addrs, pos = self._parse_spu_addrs(data, pos, header.num_spu)
        other_fx, pos = self._parse_other_fx(data, pos, header.num_other)
        engine_fx, pos = self._parse_engine_fx(data, pos, header.num_engine)
        bank_offsets, pos = self._parse_u16_array(data, pos, header.num_banks)
        song_offsets, pos = self._parse_u16_array(data, pos, header.num_songs)

        file_sectors = bytes_to_sectors(len(data))
        boundaries = self._build_boundaries(bank_offsets, song_offsets, file_sectors)

        banks = self._extract_blobs(data, bank_offsets, boundaries, file_sectors)
        songs = self._extract_blobs(data, song_offsets, boundaries, file_sectors)

        return HowlFile(
            version=header.version,
            reserved1=header.reserved1,
            reserved2=header.reserved2,
            spu_addrs=spu_addrs,
            other_fx=other_fx,
            engine_fx=engine_fx,
            banks=banks,
            songs=songs,
        )

    def read_file(self, path: str | Path) -> HowlFile:
        """Read a HWL file from disk."""
        return self.read(Path(path).read_bytes())

    def _validate_min_size(self, data: bytes) -> None:
        if len(data) < HowlHeader.SIZE:
            raise ValueError(f"Data too small for HWL header: {len(data)} < {HowlHeader.SIZE}")

    def _validate_magic(self, header: HowlHeader) -> None:
        if header.magic != HowlHeader.MAGIC:
            raise ValueError(f"Invalid HWL magic: {header.magic:#010x}, expected {HowlHeader.MAGIC:#010x}")

    def _parse_header(self, data: bytes) -> HowlHeader:
        fields = HowlHeader.STRUCT.unpack_from(data, 0)
        return HowlHeader(
            magic=fields[0],
            version=fields[1],
            reserved1=fields[2],
            reserved2=fields[3],
            num_spu=fields[4],
            num_other=fields[5],
            num_engine=fields[6],
            num_banks=fields[7],
            num_songs=fields[8],
            header_data_size=fields[9],
        )

    def _parse_spu_addrs(self, data: bytes, pos: int, count: int) -> tuple[list[SpuAddrEntry], int]:
        entries = []

        for _ in range(count):
            ptr, size = SpuAddrEntry.STRUCT.unpack_from(data, pos)
            entries.append(SpuAddrEntry(ptr, size))
            pos += SpuAddrEntry.SIZE
        
        return entries, pos

    def _parse_other_fx(self, data: bytes, pos: int, count: int) -> tuple[list[OtherFX], int]:
        entries = []
        
        for _ in range(count):
            flags, volume, pitch, spu_index, duration = OtherFX.STRUCT.unpack_from(data, pos)
            entries.append(OtherFX(flags, volume, pitch, spu_index, duration))
            pos += OtherFX.SIZE
        
        return entries, pos

    def _parse_engine_fx(self, data: bytes, pos: int, count: int) -> tuple[list[EngineFX], int]:
        entries = []
        
        for _ in range(count):
            flags, volume, pitch, unk, spu_index = EngineFX.STRUCT.unpack_from(data, pos)
            entries.append(EngineFX(flags, volume, pitch, unk, spu_index))
            pos += EngineFX.SIZE
        
        return entries, pos

    def _parse_u16_array(self, data: bytes, pos: int, count: int) -> tuple[list[int], int]:
        values = []
        
        for _ in range(count):
            val, = unpack_from("<H", data, pos)
            values.append(val)
            pos += 2
        
        return values, pos

    def _build_boundaries(
        self,
        bank_offsets: list[int],
        song_offsets: list[int],
        file_sectors: int,
    ) -> list[int]:
        return sorted(set(bank_offsets + song_offsets + [file_sectors]))

    def _extract_blobs(
        self,
        data: bytes,
        offsets: list[int],
        boundaries: list[int],
        file_sectors: int,
    ) -> list[bytes]:
        return [self._extract_single_blob(data, start, boundaries, file_sectors) for start in offsets]

    def _extract_single_blob(
        self,
        data: bytes,
        start: int,
        boundaries: list[int],
        file_sectors: int,
    ) -> bytes:
        end = self._find_next_boundary(start, boundaries, file_sectors)
        byte_start = start * SECTOR_SIZE
        byte_end = end * SECTOR_SIZE
        return data[byte_start:byte_end]

    def _find_next_boundary(self, start: int, boundaries: list[int], fallback: int) -> int:
        for b in boundaries:
            if b > start:
                return b
        
        return fallback
