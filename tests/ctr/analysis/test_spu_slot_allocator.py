# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.analysis.spu_slot_allocator import SpuSlotAllocator
from howl_editor.ctr.analysis.spu_slot_usage import SpuSlotUsageResolver
from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotLimitError
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from tests.conftest import build_bank_blob

LIMIT = constants.MAX_SPU_SLOTS


@pytest.fixture
def allocator(bank_reader, cseq_parses):
    return SpuSlotAllocator(SpuSlotUsageResolver(bank_reader, cseq_parses))


def _hwl(slots: int, free: set[int] = frozenset()) -> HowlFile:
    """A table of `slots` entries, all held by one bank except `free`."""
    held = [i for i in range(slots) if i not in free]
    bank = build_bank_blob(held, [b"\x00" * 16] * len(held))
    return HowlFile(spu_addrs=[SpuAddrEntry(0, 2) for _ in range(slots)], banks=[bank])


class TestAllocator:

    def test_appends_while_the_table_has_room(self, allocator):
        # Free slots exist, but appending keeps the existing behaviour.
        assert allocator.allocate(_hwl(10, free={3}), 2) == [10, 11]

    def test_falls_back_to_free_slots_once_the_table_is_full(self, allocator):
        assert allocator.allocate(_hwl(LIMIT, free={70, 12}), 2) == [12, 70]

    def test_mixes_remaining_room_then_free_slots(self, allocator):
        assert allocator.allocate(_hwl(LIMIT - 1, free={5}), 2) == [LIMIT - 1, 5]

    def test_refuses_when_not_enough_slots_are_left(self, allocator):
        with pytest.raises(SpuSlotLimitError):
            allocator.allocate(_hwl(LIMIT, free={5}), 2)

    def test_default_slot_is_none_when_nothing_is_left(self, allocator):
        assert allocator.default_slot(_hwl(LIMIT)) is None

    def test_default_slot_is_the_lowest_free_slot_when_full(self, allocator):
        assert allocator.default_slot(_hwl(LIMIT, free={400, 9})) == 9
