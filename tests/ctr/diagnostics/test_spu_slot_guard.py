# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotGuard, SpuSlotLimitError
from howl_editor.ctr.formats.howl.models import SpuAddrEntry

LIMIT = constants.MAX_SPU_SLOTS


def _table(count: int) -> list[SpuAddrEntry]:
    return [SpuAddrEntry(0, 1) for _ in range(count)]


class TestOutOfRange:

    def test_last_stock_slot_is_in_range(self):
        assert SpuSlotGuard().out_of_range([0, LIMIT - 1]) == []

    def test_reports_distinct_slots_past_the_table_sorted(self):
        assert SpuSlotGuard().out_of_range([LIMIT + 3, 5, LIMIT, LIMIT + 3]) == [LIMIT, LIMIT + 3]


class TestEnsureCreatable:

    def test_allows_creating_the_last_stock_slot(self):
        SpuSlotGuard().ensure_creatable(_table(LIMIT - 1), [LIMIT - 1])

    def test_refuses_creating_the_first_slot_past_the_table(self):
        with pytest.raises(SpuSlotLimitError, match=str(LIMIT)):
            SpuSlotGuard().ensure_creatable(_table(LIMIT), [LIMIT])

    def test_refuses_when_any_index_in_a_batch_crosses(self):
        with pytest.raises(SpuSlotLimitError):
            SpuSlotGuard().ensure_creatable(_table(LIMIT - 2), range(LIMIT - 2, LIMIT + 1))

    def test_reusing_an_existing_slot_past_the_table_is_not_creation(self):
        # Files that already carry extra slots must stay editable.
        SpuSlotGuard().ensure_creatable(_table(LIMIT + 6), [LIMIT + 2])
