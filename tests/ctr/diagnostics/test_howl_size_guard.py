# coding: utf-8

from howl_editor.ctr.diagnostics.howl_size_guard import HowlSizeGuard
from howl_editor.ps1.constants import SECTOR_SIZE


class TestHowlSizeGuard:

    def test_no_baseline_is_within(self):
        check = HowlSizeGuard().check(current_bytes=5 * SECTOR_SIZE, original_bytes=None)

        assert check.within_limit is True
        assert check.warning_text == ""

    def test_growth_within_same_sector_is_within(self):
        # Original uses part of a sector; new size grows but stays in that sector.
        check = HowlSizeGuard().check(
            current_bytes=3 * SECTOR_SIZE, original_bytes=3 * SECTOR_SIZE - 10,
        )

        assert check.within_limit is True
        assert check.over_sectors == 0

    def test_extra_sector_is_over(self):
        check = HowlSizeGuard().check(
            current_bytes=3 * SECTOR_SIZE + 1, original_bytes=3 * SECTOR_SIZE,
        )

        assert check.within_limit is False
        assert check.over_sectors == 1
        assert check.current_sectors == 4
        assert check.original_sectors == 3
        assert check.warning_text != ""

    def test_shrink_is_within(self):
        check = HowlSizeGuard().check(
            current_bytes=1 * SECTOR_SIZE, original_bytes=5 * SECTOR_SIZE,
        )

        assert check.within_limit is True
        assert check.over_sectors == 0
