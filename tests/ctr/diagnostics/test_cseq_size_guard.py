# coding: utf-8

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.cseq_size_guard import CseqSizeGuard
from howl_editor.ctr.formats.cseq.size_validator import CseqSizeValidator


def _guard() -> CseqSizeGuard:
    return CseqSizeGuard(CseqSizeValidator())


class TestCseqSizeGuard:

    def test_within_limit_at_exactly_the_ceiling(self):
        check = _guard().check(b"\x00" * constants.MAX_CSEQ_BYTES)

        assert check.within_limit is True
        assert check.overflow == 0
        assert check.warning_text == ""

    def test_over_limit_reports_overflow(self):
        check = _guard().check(b"\x00" * (constants.MAX_CSEQ_BYTES + 2048))

        assert check.within_limit is False
        assert check.overflow == 2048
        assert check.size == constants.MAX_CSEQ_BYTES + 2048
        assert check.warning_text != ""
