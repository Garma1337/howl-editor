# coding: utf-8

import pytest

from howl_editor.ctr.formats.howl.models import HowlHeader
from howl_editor.ctr.formats.howl.models import SpuAddrEntry, OtherFX, EngineFX
from tests.conftest import build_hwl_bytes


class TestValidateMinSize:

    def test_too_small_raises(self, howl_reader):
        with pytest.raises(ValueError, match="too small"):
            howl_reader.read(b"\x00" * 10)

    def test_exact_header_size_invalid_magic(self, howl_reader):
        with pytest.raises(ValueError, match="magic"):
            howl_reader.read(b"\x00" * HowlHeader.SIZE)


class TestParseMagic:

    def test_invalid_magic_raises(self, howl_reader):
        data = build_hwl_bytes()
        corrupted = b"\x00\x00\x00\x00" + data[4:]

        with pytest.raises(ValueError, match="magic"):
            howl_reader.read(corrupted)


class TestEmptyFile:

    def test_no_banks_no_songs(self, howl_reader):
        data = build_hwl_bytes()
        hwl = howl_reader.read(data)

        assert len(hwl.banks) == 0
        assert len(hwl.songs) == 0
        assert len(hwl.spu_addrs) == 0
        assert hwl.version == 0x80


class TestSpuAddrs:

    def test_parses_spu_entries(self, howl_reader):
        addrs = [SpuAddrEntry(0, 50), SpuAddrEntry(0, 100)]
        data = build_hwl_bytes(spu_addrs=addrs)
        hwl = howl_reader.read(data)

        assert len(hwl.spu_addrs) == 2
        assert hwl.spu_addrs[0].size == 50
        assert hwl.spu_addrs[1].size == 100


class TestEffects:

    def test_parses_other_fx(self, howl_reader):
        fx = [OtherFX(1, 128, 4096, 5, 200)]
        data = build_hwl_bytes(other_fx=fx)
        hwl = howl_reader.read(data)

        assert len(hwl.other_fx) == 1
        assert hwl.other_fx[0].flags == 1
        assert hwl.other_fx[0].volume == 128
        assert hwl.other_fx[0].spu_index == 5

    def test_parses_engine_fx(self, howl_reader):
        fx = [EngineFX(2, 200, 8192, 99, 10)]
        data = build_hwl_bytes(engine_fx=fx)
        hwl = howl_reader.read(data)

        assert len(hwl.engine_fx) == 1
        assert hwl.engine_fx[0].unk == 99
        assert hwl.engine_fx[0].spu_index == 10


class TestBanksAndSongs:

    def test_single_bank(self, howl_reader):
        bank = b"\xAA" * 512
        data = build_hwl_bytes(banks=[bank])
        hwl = howl_reader.read(data)

        assert len(hwl.banks) == 1
        assert hwl.banks[0][:512] == bank

    def test_single_song(self, howl_reader):
        song = b"\xBB" * 256
        data = build_hwl_bytes(songs=[song])
        hwl = howl_reader.read(data)

        assert len(hwl.songs) == 1
        assert hwl.songs[0][:256] == song

    def test_multiple_banks_and_songs(self, howl_reader):
        banks = [b"\x01" * 100, b"\x02" * 200]
        songs = [b"\x03" * 150, b"\x04" * 50, b"\x05" * 300]
        data = build_hwl_bytes(banks=banks, songs=songs)
        hwl = howl_reader.read(data)

        assert len(hwl.banks) == 2
        assert len(hwl.songs) == 3
        assert hwl.banks[0][:100] == b"\x01" * 100
        assert hwl.banks[1][:200] == b"\x02" * 200
        assert hwl.songs[0][:150] == b"\x03" * 150

    def test_bank_blob_is_sector_aligned(self, howl_reader):
        bank = b"\xFF" * 100
        data = build_hwl_bytes(banks=[bank])
        hwl = howl_reader.read(data)

        assert len(hwl.banks[0]) % 0x800 == 0


class TestBoundaryDetection:

    def test_adjacent_blobs_dont_overlap(self, howl_reader):
        bank1 = b"\x01" * 2048
        bank2 = b"\x02" * 2048
        data = build_hwl_bytes(banks=[bank1, bank2])
        hwl = howl_reader.read(data)

        assert hwl.banks[0][:2048] == b"\x01" * 2048
        assert hwl.banks[1][:2048] == b"\x02" * 2048


class TestFindNextBoundary:

    def test_finds_next(self, howl_reader):
        assert howl_reader._find_next_boundary(5, [3, 5, 10, 20], 100) == 10

    def test_returns_fallback(self, howl_reader):
        assert howl_reader._find_next_boundary(30, [3, 5, 10, 20], 100) == 100
