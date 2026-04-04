# coding: utf-8

from howl_editor.constants import (
    bytes_to_sectors, SECTOR_SIZE,
    HEADER_SIZE, SPU_ADDR_SIZE, OTHER_FX_SIZE, ENGINE_FX_SIZE,
)


class TestBytesToSectors:
    def test_zero(self):
        assert bytes_to_sectors(0) == 0

    def test_one_byte(self):
        assert bytes_to_sectors(1) == 1

    def test_exact_sector(self):
        assert bytes_to_sectors(SECTOR_SIZE) == 1

    def test_one_over(self):
        assert bytes_to_sectors(SECTOR_SIZE + 1) == 2

    def test_two_sectors(self):
        assert bytes_to_sectors(SECTOR_SIZE * 2) == 2


class TestStructSizes:
    def test_header_size(self):
        assert HEADER_SIZE == 40

    def test_spu_addr_size(self):
        assert SPU_ADDR_SIZE == 4

    def test_other_fx_size(self):
        assert OTHER_FX_SIZE == 8

    def test_engine_fx_size(self):
        assert ENGINE_FX_SIZE == 8
