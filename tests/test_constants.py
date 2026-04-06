# coding: utf-8

from howl_editor.models import HowlHeader, SpuAddrEntry, OtherFX, EngineFX
from howl_editor.models.howl import SECTOR_SIZE, bytes_to_sectors


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
        assert HowlHeader.SIZE == 40

    def test_spu_addr_size(self):
        assert SpuAddrEntry.SIZE == 4

    def test_other_fx_size(self):
        assert OtherFX.SIZE == 8

    def test_engine_fx_size(self):
        assert EngineFX.SIZE == 8
