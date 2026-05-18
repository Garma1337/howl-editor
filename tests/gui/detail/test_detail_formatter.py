# coding: utf-8

from pathlib import Path

from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.core.template_engine import TemplateEngine
from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.gui.detail.bank_detail_formatter import BankDetailFormatter
from howl_editor.gui.detail.detail_formatter import DetailFormatter
from howl_editor.gui.detail.fx_detail_formatter import FxDetailFormatter
from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.gui.detail.song_detail_formatter import SongDetailFormatter
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.ctr.formats.howl.version import HowlVersionDetector
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "howl_editor" / "gui" / "templates"


class TestDetailFormatter:

    def test_facade_exposes_sub_formatters(self):
        vlq = VlqCodec()
        engine = TemplateEngine(_TEMPLATE_DIR)
        sizes = SizeFormatter()

        fmt = DetailFormatter(
            howl_formatter=HowlDetailFormatter(HowlVersionDetector(), engine, sizes),
            fx_formatter=FxDetailFormatter(engine),
            bank_formatter=BankDetailFormatter(BankReader(StockNameResolver()), engine, sizes),
            song_formatter=SongDetailFormatter(CseqReader(vlq, StockNameResolver()), engine, sizes),
        )

        assert isinstance(fmt.howl, HowlDetailFormatter)
        assert isinstance(fmt.fx, FxDetailFormatter)
        assert isinstance(fmt.bank, BankDetailFormatter)
        assert isinstance(fmt.song, SongDetailFormatter)
