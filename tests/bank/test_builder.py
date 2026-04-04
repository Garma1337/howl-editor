"""Tests for BankBuilder."""

from struct import unpack_from

import pytest

from howl_editor.models import SpuAddrEntry, VagSample, BankBuildResult
from howl_editor.bank.builder import BankBuilder
from howl_editor.vag.reader import VagReader
from howl_editor.constants import SECTOR_SIZE


class TestBuildFromSamples:
    def test_single_sample(self, bank_builder):
        samples = [VagSample(data=b"\xAA" * 80)]
        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=0)
        assert isinstance(result, BankBuildResult)
        assert result.new_spu_indices == [0]
        assert len(spu_addrs) == 1
        assert spu_addrs[0].size == 10  # 80 / 8

    def test_multiple_samples(self, bank_builder):
        samples = [VagSample(data=b"\x01" * 160), VagSample(data=b"\x02" * 240)]
        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=0)
        assert result.new_spu_indices == [0, 1]
        assert len(spu_addrs) == 2
        assert spu_addrs[0].size == 20
        assert spu_addrs[1].size == 30

    def test_start_index_offset(self, bank_builder):
        samples = [VagSample(data=b"\x00" * 80)]
        spu_addrs = [SpuAddrEntry(0, 50)]  # Existing entry at index 0
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=5)
        assert result.new_spu_indices == [5]
        assert len(spu_addrs) == 6
        assert spu_addrs[5].size == 10

    def test_bank_data_structure(self, bank_builder):
        samples = [VagSample(data=b"\xFF" * 80)]
        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=0)
        blob = result.bank_data
        # Header: num_samples=1, sample_id=0
        num = unpack_from("<H", blob, 0)[0]
        assert num == 1
        sid = unpack_from("<h", blob, 2)[0]
        assert sid == 0
        # Data starts at sector boundary
        assert blob[SECTOR_SIZE:SECTOR_SIZE + 80] == b"\xFF" * 80


class TestBuildFromRaw:
    def test_builds_blob(self, bank_builder):
        blob = bank_builder.build_from_raw([(10, b"\xAA" * 40), (20, b"\xBB" * 80)])
        num = unpack_from("<H", blob, 0)[0]
        assert num == 2
        id1 = unpack_from("<h", blob, 2)[0]
        id2 = unpack_from("<h", blob, 4)[0]
        assert id1 == 10
        assert id2 == 20
        assert blob[SECTOR_SIZE:SECTOR_SIZE + 40] == b"\xAA" * 40
        assert blob[SECTOR_SIZE + 40:SECTOR_SIZE + 120] == b"\xBB" * 80


class TestBuildFromFiles:
    def test_builds_from_vag_files(self, bank_builder, tmp_path):
        # Create temp VAG files
        from tests.conftest import build_vag_bytes
        vag_data = b"\xCC" * 32
        vag1 = tmp_path / "sample1.vag"
        vag1.write_bytes(build_vag_bytes(data=vag_data, name="s1"))

        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_files([vag1], spu_addrs)
        assert result.new_spu_indices == [0]
        assert spu_addrs[0].size == 4  # 32 / 8
        assert vag_data in result.bank_data


class TestPadToSector:
    def test_pads_short_data(self, bank_builder):
        padded = bank_builder._pad_to_sector(b"\x00" * 10)
        assert len(padded) == SECTOR_SIZE
        assert padded[:10] == b"\x00" * 10

    def test_exact_sector(self, bank_builder):
        padded = bank_builder._pad_to_sector(b"\x00" * SECTOR_SIZE)
        assert len(padded) == SECTOR_SIZE
