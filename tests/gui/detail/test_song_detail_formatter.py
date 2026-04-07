# coding: utf-8

from pathlib import Path

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.reader import CseqReader
from howl_editor.gui.detail.song_detail_formatter import SongDetailFormatter
from howl_editor.models import CseqInstrument
from howl_editor.models import HowlFile
from tests.conftest import build_cseq_bytes

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "howl_editor" / "gui" / "templates"


def _formatter():
    return SongDetailFormatter(CseqReader(VlqCodec()), TemplateEngine(_TEMPLATE_DIR))


class TestSongDetailFormatter:

    def test_format_summary(self):
        fmt = _formatter()
        cseq = build_cseq_bytes()
        hwl = HowlFile(songs=[cseq])
        text = fmt.format_summary(hwl)

        assert "Songs (1)" in text
        assert "bytes" in text.lower()

    def test_format_summary_includes_name(self):
        fmt = _formatter()
        cseq = build_cseq_bytes()
        hwl = HowlFile(songs=[cseq])
        text = fmt.format_summary(hwl)

        assert "Dingo Canyon" in text

    def test_format_summary_empty(self):
        fmt = _formatter()
        text = fmt.format_summary(HowlFile())

        assert "Songs (0)" in text

    def test_format_tree_info(self):
        fmt = _formatter()
        cseq = build_cseq_bytes()
        text = fmt.format_tree_info(cseq)

        assert "seq" in text

    def test_format_tree_info_invalid(self):
        fmt = _formatter()
        text = fmt.format_tree_info(b"\x00")

        assert "bytes" in text

    def test_format_details(self):
        fmt = _formatter()
        cseq = build_cseq_bytes()
        hwl = HowlFile(songs=[cseq])
        text = fmt.format_details(hwl, 0)

        assert "Song 0" in text
        assert "Dingo Canyon" in text
        assert "Instruments:" not in text or "Sequences:" in text

    def test_format_details_with_instruments(self):
        fmt = _formatter()
        cseq = build_cseq_bytes(instruments=[CseqInstrument(sample_id=5, frequency=0x1000)])
        hwl = HowlFile(songs=[cseq])
        text = fmt.format_details(hwl, 0)

        assert "Instruments" in text
