# coding: utf-8

from struct import unpack_from

import pytest

from howl_editor.models import HowlFile, SpuAddrEntry, OtherFX, EngineFX
from howl_editor.howl.writer import HowlWriter, HowlLayout
from howl_editor.constants import HWL_MAGIC, SECTOR_SIZE, HEADER_SIZE


class TestSerializeEmpty:
    def test_produces_one_sector(self, howl_writer):
        hwl = HowlFile()
        data = howl_writer.serialize(hwl)
        assert len(data) == SECTOR_SIZE

    def test_has_magic(self, howl_writer):
        hwl = HowlFile()
        data = howl_writer.serialize(hwl)
        magic = unpack_from("<I", data, 0)[0]
        assert magic == HWL_MAGIC

    def test_has_version(self, howl_writer):
        hwl = HowlFile(version=0x80)
        data = howl_writer.serialize(hwl)
        version = unpack_from("<I", data, 4)[0]
        assert version == 0x80


class TestSerializeWithData:
    def test_spu_addrs_roundtrip(self, howl_writer):
        hwl = HowlFile(spu_addrs=[SpuAddrEntry(0, 42)])
        data = howl_writer.serialize(hwl)
        # SPU table at offset 40
        ptr, size = unpack_from("<HH", data, HEADER_SIZE)
        assert ptr == 0
        assert size == 42

    def test_bank_data_preserved(self, howl_writer):
        bank_content = b"\xDE\xAD\xBE\xEF"
        hwl = HowlFile(banks=[bank_content])
        data = howl_writer.serialize(hwl)
        # Bank starts at sector 1 (header uses sector 0)
        assert data[SECTOR_SIZE:SECTOR_SIZE + 4] == bank_content

    def test_song_data_preserved(self, howl_writer):
        song_content = b"\xCA\xFE"
        hwl = HowlFile(songs=[song_content])
        data = howl_writer.serialize(hwl)
        assert data[SECTOR_SIZE:SECTOR_SIZE + 2] == song_content


class TestSectorAlignment:
    def test_output_is_sector_aligned(self, howl_writer):
        hwl = HowlFile(banks=[b"\x01" * 100], songs=[b"\x02" * 200])
        data = howl_writer.serialize(hwl)
        assert len(data) % SECTOR_SIZE == 0

    def test_bank_after_song_no_overlap(self, howl_writer):
        bank = b"\xAA" * 2050  # slightly over 1 sector
        song = b"\xBB" * 100
        hwl = HowlFile(banks=[bank], songs=[song])
        data = howl_writer.serialize(hwl)
        # Bank takes 2 sectors, song should be at sector 3 or later
        # Find song content
        assert song in data


class TestCalculateLayout:
    def test_empty(self, howl_writer):
        hwl = HowlFile()
        layout = howl_writer._calculate_layout(hwl)
        assert isinstance(layout, HowlLayout)
        assert layout.bank_offsets == []
        assert layout.song_offsets == []
        assert layout.total_sectors == layout.header_sectors

    def test_with_banks(self, howl_writer):
        hwl = HowlFile(banks=[b"\x00" * SECTOR_SIZE, b"\x00" * SECTOR_SIZE])
        layout = howl_writer._calculate_layout(hwl)
        assert len(layout.bank_offsets) == 2
        assert layout.bank_offsets[1] == layout.bank_offsets[0] + 1

    def test_songs_after_banks(self, howl_writer):
        hwl = HowlFile(banks=[b"\x00" * SECTOR_SIZE], songs=[b"\x00" * SECTOR_SIZE])
        layout = howl_writer._calculate_layout(hwl)
        assert layout.song_offsets[0] > layout.bank_offsets[0]


class TestHeaderDataSize:
    def test_header_data_size_field(self, howl_writer):
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry()] * 2,
            other_fx=[OtherFX()],
            banks=[b"\x00"],
        )
        data = howl_writer.serialize(hwl)
        stored_size = unpack_from("<I", data, 36)[0]
        assert stored_size == hwl.header_data_size
