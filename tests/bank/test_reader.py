# coding: utf-8

import pytest
from howl_editor.models import SpuAddrEntry, BankSample
from howl_editor.bank.reader import BankReader
from tests.conftest import build_bank_blob


class TestReadSampleCount:
    def test_empty_data(self, bank_reader):
        assert bank_reader._read_sample_count(b"") == 0

    def test_one_byte(self, bank_reader):
        assert bank_reader._read_sample_count(b"\x00") == 0

    def test_normal_count(self, bank_reader):
        assert bank_reader._read_sample_count(b"\x03\x00") == 3

    def test_too_large_returns_zero(self, bank_reader):
        assert bank_reader._read_sample_count(b"\x00\x04") == 0  # 1024


class TestParseBankBlob:
    def test_empty_bank(self, bank_reader):
        result = bank_reader.parse(b"", [])
        assert result == []

    def test_single_sample(self, bank_reader):
        sample_data = b"\xFF" * 800
        spu_addrs = [SpuAddrEntry(0, 100)]  # 100 * 8 = 800 bytes
        blob = build_bank_blob([0], [sample_data])
        result = bank_reader.parse(blob, spu_addrs)
        assert len(result) == 1
        assert isinstance(result[0], BankSample)
        assert result[0].spu_index == 0
        assert result[0].data == sample_data

    def test_multiple_samples(self, bank_reader):
        data1 = b"\xAA" * 80
        data2 = b"\xBB" * 160
        spu_addrs = [SpuAddrEntry(0, 10), SpuAddrEntry(0, 20)]
        blob = build_bank_blob([0, 1], [data1, data2])
        result = bank_reader.parse(blob, spu_addrs)
        assert len(result) == 2
        assert result[0].spu_index == 0
        assert result[0].data == data1
        assert result[1].spu_index == 1
        assert result[1].data == data2

    def test_skips_invalid_spu_index(self, bank_reader):
        spu_addrs = [SpuAddrEntry(0, 10)]  # Only index 0 exists
        blob = build_bank_blob([0, 99], [b"\x00" * 80, b"\x00" * 80])
        result = bank_reader.parse(blob, spu_addrs)
        assert len(result) == 1
        assert result[0].spu_index == 0


class TestGetName:
    def test_known_bank(self, bank_reader):
        assert bank_reader.get_name(0) != ""
        assert bank_reader.get_name(1) != ""

    def test_known_bank_returns_string(self, bank_reader):
        name = bank_reader.get_name(0)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_custom_bank(self, bank_reader):
        assert bank_reader.get_name(71) == "Custom"
        assert bank_reader.get_name(100) == "Custom"


class TestCalculateDataOffset:
    def test_small_header(self, bank_reader):
        # 2 + 1*2 = 4 bytes header -> rounds up to 1 sector = 0x800
        assert bank_reader._calculate_data_offset(1) == 0x800

    def test_large_header(self, bank_reader):
        # 2 + 1000*2 = 2002 bytes -> rounds up to 1 sector = 0x800
        assert bank_reader._calculate_data_offset(1000) == 0x800
