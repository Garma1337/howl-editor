# coding: utf-8

from howl_editor.ctr.constants import MAX_CSEQ_BYTES
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator


class TestIsWithinLimit:

    def test_empty_data_is_within_limit(self):
        assert CseqSizeValidator().is_within_limit(b"") is True

    def test_exactly_at_limit_is_within(self):
        data = b"\x00" * MAX_CSEQ_BYTES

        assert CseqSizeValidator().is_within_limit(data) is True

    def test_one_byte_over_is_not_within(self):
        data = b"\x00" * (MAX_CSEQ_BYTES + 1)

        assert CseqSizeValidator().is_within_limit(data) is False


class TestOverflowBytes:

    def test_returns_zero_when_within_limit(self):
        validator = CseqSizeValidator()

        assert validator.calculate_overflow_bytes(b"\x00" * 100) == 0
        assert validator.calculate_overflow_bytes(b"\x00" * MAX_CSEQ_BYTES) == 0

    def test_returns_difference_when_over(self):
        data = b"\x00" * (MAX_CSEQ_BYTES + 42)

        assert CseqSizeValidator().calculate_overflow_bytes(data) == 42
