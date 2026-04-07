# coding: utf-8

from howl_editor.models import HowlFile, SpuAddrEntry, OtherFX, EngineFX
from tests.conftest import build_hwl_bytes


class TestRoundTrip:

    def test_empty_roundtrip(self, howl_reader, howl_writer):
        hwl = HowlFile()
        data = howl_writer.serialize(hwl)
        hwl2 = howl_reader.read(data)

        assert hwl2.version == hwl.version
        assert len(hwl2.banks) == 0
        assert len(hwl2.songs) == 0

    def test_full_roundtrip(self, howl_reader, howl_writer):
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 50), SpuAddrEntry(0, 100)],
            other_fx=[OtherFX(1, 128, 4096, 0, 200), OtherFX(2, 64, 2048, 1, 100)],
            engine_fx=[EngineFX(1, 200, 8192, 99, 5)],
            banks=[b"\xAA" * 500, b"\xBB" * 3000],
            songs=[b"\xCC" * 100],
        )

        data = howl_writer.serialize(hwl)
        hwl2 = howl_reader.read(data)

        assert hwl2.version == hwl.version
        assert len(hwl2.spu_addrs) == 2
        assert hwl2.spu_addrs[0].size == 50
        assert hwl2.spu_addrs[1].size == 100
        assert len(hwl2.other_fx) == 2
        assert hwl2.other_fx[0].volume == 128
        assert hwl2.other_fx[1].spu_index == 1
        assert len(hwl2.engine_fx) == 1
        assert hwl2.engine_fx[0].unk == 99
        assert len(hwl2.banks) == 2
        assert hwl2.banks[0][:500] == b"\xAA" * 500
        assert hwl2.banks[1][:3000] == b"\xBB" * 3000
        assert len(hwl2.songs) == 1
        assert hwl2.songs[0][:100] == b"\xCC" * 100

    def test_binary_roundtrip(self, howl_reader, howl_writer):
        """Read manually built bytes, write, read again - should match."""
        spu = [SpuAddrEntry(0, 10)]
        fx = [OtherFX(1, 100, 1000, 0, 50)]
        bank = b"\x01" * 1024
        song = b"\x02" * 512
        original = build_hwl_bytes(spu_addrs=spu, other_fx=fx, banks=[bank], songs=[song])

        hwl = howl_reader.read(original)
        rewritten = howl_writer.serialize(hwl)
        hwl2 = howl_reader.read(rewritten)

        assert hwl2.spu_addrs[0].size == 10
        assert hwl2.other_fx[0].volume == 100
        assert hwl2.banks[0][:1024] == bank
        assert hwl2.songs[0][:512] == song
