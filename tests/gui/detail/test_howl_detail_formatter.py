# coding: utf-8

from pathlib import Path

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.models import HowlFile, SpuAddrEntry, OtherFX, EngineFX

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "howl_editor" / "gui" / "templates"


def _formatter():
    engine = TemplateEngine(_TEMPLATE_DIR)
    return HowlDetailFormatter(HowlVersionDetector(), engine)


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
        assert "SPU Entries" in text
        assert ">1<" in text  # value in table cell

    def test_format_details_with_path(self):
        fmt = _formatter()
        text = fmt.format_details(HowlFile(), "/tmp/test.hwl")

        assert "/tmp/test.hwl" in text

    def test_format_details_without_path(self):
        fmt = _formatter()
        text = fmt.format_details(HowlFile(), None)

        assert "File" not in text or text.count("File") == text.count("HOWL File")

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
