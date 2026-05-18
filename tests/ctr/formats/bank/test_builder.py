# coding: utf-8

import struct

import pytest

from howl_editor.ctr.formats.bank.models import BankSample, BankBuildResult
from howl_editor.ctr.formats.howl.models import SpuAddrEntry
from howl_editor.ps1.constants import SECTOR_SIZE
from howl_editor.ps1.formats.vag.models import VagSample
from tests.conftest import build_vag_bytes


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
        num = struct.unpack_from("<H", blob, 0)[0]
        assert num == 1

        sid = struct.unpack_from("<h", blob, 2)[0]
        assert sid == 0

        # Data starts at sector boundary
        assert blob[SECTOR_SIZE:SECTOR_SIZE + 80] == b"\xFF" * 80

    def test_records_sample_rate_per_vag(self, bank_builder):
        # Different headered VAGs should produce a parallel sample_rates list
        # so callers can propagate the rates into OtherFX entries.
        samples = [
            VagSample(data=b"\x01" * 80, sample_rate=44100),
            VagSample(data=b"\x02" * 80, sample_rate=22050),
            VagSample(data=b"\x03" * 80, sample_rate=11025),
        ]
        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=0)

        assert result.sample_rates == [44100, 22050, 11025]
        assert len(result.sample_rates) == len(result.new_spu_indices)

    def test_sample_rates_default_when_header_absent(self, bank_builder):
        # VagSample defaults sample_rate to 44100 for headerless data;
        # the builder must carry that default through verbatim.
        samples = [VagSample(data=b"\x00" * 80)]
        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_samples(samples, spu_addrs, start_index=0)

        assert result.sample_rates == [44100]


class TestBuildFromRaw:

    def test_builds_blob(self, bank_builder):
        blob = bank_builder.build_from_raw([(10, b"\xAA" * 40), (20, b"\xBB" * 80)])
        num = struct.unpack_from("<H", blob, 0)[0]
        assert num == 2

        id1 = struct.unpack_from("<h", blob, 2)[0]
        id2 = struct.unpack_from("<h", blob, 4)[0]

        assert id1 == 10
        assert id2 == 20
        assert blob[SECTOR_SIZE:SECTOR_SIZE + 40] == b"\xAA" * 40
        assert blob[SECTOR_SIZE + 40:SECTOR_SIZE + 120] == b"\xBB" * 80


class TestBuildFromFiles:

    def test_builds_from_vag_files(self, bank_builder, tmp_path):
        # Create temp VAG files
        vag_data = b"\xCC" * 32
        vag1 = tmp_path / "sample1.vag"
        vag1.write_bytes(build_vag_bytes(data=vag_data, name="s1"))

        spu_addrs: list[SpuAddrEntry] = []
        result = bank_builder.build_from_files([vag1], spu_addrs)

        assert result.new_spu_indices == [0]
        assert spu_addrs[0].size == 4  # 32 / 8
        assert vag_data in result.bank_data


class TestMerge:

    def test_builds_from_bank_samples(self, bank_builder):
        samples = [
            BankSample(spu_index=10, data=b"\xAA" * 80),
            BankSample(spu_index=5, data=b"\xBB" * 40),
        ]

        blob = bank_builder.merge(samples)
        num = struct.unpack_from("<H", blob, 0)[0]
        assert num == 2

        id0 = struct.unpack_from("<h", blob, 2)[0]
        id1 = struct.unpack_from("<h", blob, 4)[0]

        assert id0 == 10
        assert id1 == 5
        assert blob[SECTOR_SIZE:SECTOR_SIZE + 80] == b"\xAA" * 80
        assert blob[SECTOR_SIZE + 80:SECTOR_SIZE + 120] == b"\xBB" * 40

    def test_preserves_order(self, bank_builder):
        samples = [
            BankSample(spu_index=99, data=b"\x01" * 16),
            BankSample(spu_index=2, data=b"\x02" * 16),
            BankSample(spu_index=50, data=b"\x03" * 16),
        ]

        blob = bank_builder.merge(samples)
        ids = [struct.unpack_from("<h", blob, 2 + i * 2)[0] for i in range(3)]

        assert ids == [99, 2, 50]

    def test_empty_list(self, bank_builder):
        blob = bank_builder.merge([])
        num = struct.unpack_from("<H", blob, 0)[0]

        assert num == 0


class TestRemoveSample:

    def test_removes_by_index(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 31

        blob = bank_builder.merge([
            BankSample(spu_index=10, data=b"\xAA" * 16),
            BankSample(spu_index=20, data=b"\xBB" * 16),
            BankSample(spu_index=30, data=b"\xCC" * 16),
        ])

        new_blob = bank_builder.remove_sample(blob, spu, 1, bank_reader)
        parsed = bank_reader.parse(new_blob, spu)

        assert len(parsed) == 2
        assert parsed[0].spu_index == 10
        assert parsed[1].spu_index == 30

    def test_out_of_range_raises(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 5
        blob = bank_builder.merge([BankSample(spu_index=0, data=b"\x00" * 16)])

        with pytest.raises(IndexError):
            bank_builder.remove_sample(blob, spu, 5, bank_reader)


class TestAddSample:

    def test_appends_sample(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 5
        blob = bank_builder.merge([BankSample(spu_index=0, data=b"\xAA" * 16)])
        new_blob = bank_builder.add_sample(blob, spu, b"\xBB" * 32, bank_reader)
        parsed = bank_reader.parse(new_blob, spu)

        assert len(parsed) == 2
        assert parsed[0].spu_index == 0
        assert parsed[1].data == b"\xBB" * 32

    def test_creates_spu_entry(self, bank_builder, bank_reader):
        spu: list[SpuAddrEntry] = []
        blob = bank_builder.merge([])
        bank_builder.add_sample(blob, spu, b"\x00" * 24, bank_reader)

        assert len(spu) == 1
        assert spu[0].byte_size == 24

    def test_explicit_spu_index(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 0)] * 10
        blob = bank_builder.merge([])
        new_blob = bank_builder.add_sample(blob, spu, b"\x00" * 16, bank_reader, spu_index=5)
        parsed = bank_reader.parse(new_blob, spu)

        assert len(parsed) == 1
        assert parsed[0].spu_index == 5


class TestReplaceSample:

    def test_replaces_data(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 5

        blob = bank_builder.merge([
            BankSample(spu_index=3, data=b"\xAA" * 16),
        ])

        new_blob = bank_builder.replace_sample(blob, spu, 0, b"\xBB" * 32, bank_reader)
        parsed = bank_reader.parse(new_blob, spu)

        assert len(parsed) == 1
        assert parsed[0].spu_index == 3
        assert parsed[0].data == b"\xBB" * 32

    def test_updates_spu_size(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 5
        blob = bank_builder.merge([BankSample(spu_index=2, data=b"\x00" * 16)])
        bank_builder.replace_sample(blob, spu, 0, b"\x00" * 48, bank_reader)

        assert spu[2].byte_size == 48

    def test_out_of_range_raises(self, bank_builder, bank_reader):
        spu = [SpuAddrEntry(0, 2)] * 5
        blob = bank_builder.merge([BankSample(spu_index=0, data=b"\x00" * 16)])

        with pytest.raises(IndexError):
            bank_builder.replace_sample(blob, spu, 3, b"\x00" * 16, bank_reader)


class TestPadToSector:

    def test_pads_short_data(self, bank_builder):
        padded = bank_builder._pad_to_sector(b"\x00" * 10)

        assert len(padded) == SECTOR_SIZE
        assert padded[:10] == b"\x00" * 10

    def test_exact_sector(self, bank_builder):
        padded = bank_builder._pad_to_sector(b"\x00" * SECTOR_SIZE)

        assert len(padded) == SECTOR_SIZE
