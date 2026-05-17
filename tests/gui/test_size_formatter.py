# coding: utf-8

import pytest

from howl_editor.gui.size_formatter import SizeFormatter


@pytest.fixture
def size_formatter():
    return SizeFormatter()


class TestFormatBytes:

    def test_below_kb_shows_bytes(self, size_formatter):
        assert size_formatter.format_bytes(0) == "0 B"
        assert size_formatter.format_bytes(512) == "512 B"
        assert size_formatter.format_bytes(1023) == "1,023 B"

    def test_kb_range_one_decimal(self, size_formatter):
        assert size_formatter.format_bytes(1024) == "1.0 KB"
        assert size_formatter.format_bytes(1536) == "1.5 KB"
        assert size_formatter.format_bytes(10240) == "10.0 KB"

    def test_mb_range_two_decimals(self, size_formatter):
        assert size_formatter.format_bytes(1024 * 1024) == "1.00 MB"
        assert size_formatter.format_bytes(int(1.5 * 1024 * 1024)) == "1.50 MB"

    def test_thousands_separators_in_kb(self, size_formatter):
        # Just under 1 MB so we stay in the KB branch with a 4-digit number.
        result = size_formatter.format_bytes(1000 * 1024)  # 1000.0 KB

        assert "1,000.0 KB" == result


class TestFormatSpuUsage:

    def test_pair(self, size_formatter):
        result = size_formatter.format_spu_usage(100_000, 512 * 1024)

        assert "/" in result
        assert "97.7 KB" in result   # ~100,000 bytes
        assert "512.0 KB" in result


class TestPercentage:

    def test_partial(self, size_formatter):
        assert size_formatter.percentage(256, 1024) == 25.0

    def test_zero_total_returns_zero(self, size_formatter):
        assert size_formatter.percentage(100, 0) == 0.0

    def test_clamped_to_100(self, size_formatter):
        assert size_formatter.percentage(2000, 1000) == 100.0

    def test_clamped_to_zero_for_negative(self, size_formatter):
        assert size_formatter.percentage(-10, 100) == 0.0
