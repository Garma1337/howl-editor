# coding: utf-8

from howl_editor.ctr.formats.howl.models import SpuAddrEntry, OtherFX, EngineFX, HowlFile, HowlHeader


class TestSpuAddrEntry:

    def test_defaults(self):
        e = SpuAddrEntry()

        assert e.ptr == 0
        assert e.size == 0

    def test_byte_size(self):
        e = SpuAddrEntry(0, 100)

        assert e.byte_size == 800

    def test_byte_size_zero(self):
        e = SpuAddrEntry(0, 0)

        assert e.byte_size == 0


class TestHowlFile:

    def test_defaults(self):
        hwl = HowlFile()

        assert hwl.version == 0x80
        assert hwl.banks == []
        assert hwl.songs == []

    def test_header_data_size_empty(self):
        hwl = HowlFile()

        assert hwl.header_data_size == 0

    def test_header_data_size_with_data(self):
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry()] * 3,
            other_fx=[OtherFX()] * 2,
            engine_fx=[EngineFX()] * 1,
            banks=[b"x"] * 4,
            songs=[b"y"] * 5,
        )

        expected = 3 * 4 + 2 * 8 + 1 * 8 + 4 * 2 + 5 * 2

        assert hwl.header_data_size == expected


class TestHowlFileReserved:

    def test_reserved_defaults(self):
        hwl = HowlFile()

        assert hwl.reserved1 == 0
        assert hwl.reserved2 == 0


class TestHowlHeader:

    def test_defaults(self):
        h = HowlHeader()

        assert h.magic == 0
        assert h.version == 0x80
        assert h.reserved1 == 0
        assert h.reserved2 == 0
