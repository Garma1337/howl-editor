# coding: utf-8

from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.models import HowlFile, SpuAddrEntry, OtherFX, EngineFX


def _formatter():
    return HowlDetailFormatter(HowlVersionDetector())


class TestHowlDetailFormatter:

    def test_format_details_basic(self):
        fmt = _formatter()

        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 10)],
            other_fx=[OtherFX()],
            engine_fx=[EngineFX()],
            banks=[b"\x00" * 100],
            songs=[b"\x00" * 50],
        )

        text = fmt.format_details(hwl, None)

        assert "HOWL File" in text
        assert "SPU Entries:  1" in text
        assert "Banks:       1" in text
        assert "Songs:       1" in text

    def test_format_details_with_path(self):
        fmt = _formatter()
        text = fmt.format_details(HowlFile(), "/tmp/test.hwl")

        assert "/tmp/test.hwl" in text

    def test_format_details_without_path(self):
        fmt = _formatter()
        text = fmt.format_details(HowlFile(), None)

        assert "File:" not in text

    def test_format_spu_table(self):
        fmt = _formatter()
        hwl = HowlFile(spu_addrs=[SpuAddrEntry(0, 10), SpuAddrEntry(100, 20)])

        text = fmt.format_spu_table(hwl)
        assert "2 entries" in text
        assert "80" in text  # 10 * 8 bytes

    def test_format_spu_table_empty(self):
        fmt = _formatter()
        text = fmt.format_spu_table(HowlFile())

        assert "0 entries" in text
