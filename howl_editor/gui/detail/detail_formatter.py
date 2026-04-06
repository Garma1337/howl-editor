# coding: utf-8

from howl_editor.gui.detail.howl_detail_formatter import HowlDetailFormatter
from howl_editor.gui.detail.fx_detail_formatter import FxDetailFormatter
from howl_editor.gui.detail.bank_detail_formatter import BankDetailFormatter
from howl_editor.gui.detail.song_detail_formatter import SongDetailFormatter


class DetailFormatter:
    """Facade that composes all detail formatters."""

    def __init__(
        self,
        howl_formatter: HowlDetailFormatter,
        fx_formatter: FxDetailFormatter,
        bank_formatter: BankDetailFormatter,
        song_formatter: SongDetailFormatter,
    ):
        self.howl = howl_formatter
        self.fx = fx_formatter
        self.bank = bank_formatter
        self.song = song_formatter
