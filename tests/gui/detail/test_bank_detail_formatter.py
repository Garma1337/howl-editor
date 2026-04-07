# coding: utf-8

from howl_editor.bank.reader import BankReader
from howl_editor.gui.detail.bank_detail_formatter import BankDetailFormatter
from howl_editor.models import HowlFile, SpuAddrEntry
from tests.conftest import build_bank_blob


def _formatter():
    return BankDetailFormatter(BankReader())


def _hwl_with_bank():
    blob = build_bank_blob([0, 1], [b"\x00" * 16, b"\x00" * 16])

    return HowlFile(
        spu_addrs=[SpuAddrEntry(0, 2), SpuAddrEntry(0, 2)],
        banks=[blob],
    )


class TestBankDetailFormatter:

    def test_format_summary(self):
        fmt = _formatter()
        text = fmt.format_summary(_hwl_with_bank())

        assert "Banks (1)" in text
        assert "bytes" in text.lower()

    def test_format_summary_empty(self):
        fmt = _formatter()
        text = fmt.format_summary(HowlFile())

        assert "Banks (0)" in text

    def test_format_summary_includes_name(self):
        fmt = _formatter()
        hwl = _hwl_with_bank()
        text = fmt.format_summary(hwl)

        assert "SFX" in text

    def test_format_tree_info_with_samples(self):
        fmt = _formatter()
        blob = build_bank_blob([0], [b"\x00" * 16])
        text = fmt.format_tree_info(blob)

        assert "1 samples" in text

    def test_format_tree_info_empty(self):
        fmt = _formatter()
        text = fmt.format_tree_info(b"\x00\x00")

        assert "bytes" in text

    def test_format_details(self):
        fmt = _formatter()
        hwl = _hwl_with_bank()
        text = fmt.format_details(hwl, 0)

        assert "Bank 0" in text
        assert "Samples: 2" in text
        assert "Sample IDs:" in text
