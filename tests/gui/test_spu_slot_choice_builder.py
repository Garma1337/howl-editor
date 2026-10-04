# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.analysis.spu_slot_allocator import SpuSlotAllocator
from howl_editor.ctr.analysis.spu_slot_usage import SpuSlotUsageResolver
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.gui.spu_slot_choice_builder import SpuSlotChoiceBuilder
from tests.conftest import build_bank_blob

LIMIT = constants.MAX_SPU_SLOTS


@pytest.fixture
def builder(bank_reader, cseq_parse_cache):
    usage = SpuSlotUsageResolver(bank_reader, cseq_parse_cache)
    return SpuSlotChoiceBuilder(bank_reader, usage, SpuSlotAllocator(usage))


def _hwl(slots: int, held: list[int]) -> HowlFile:
    bank = build_bank_blob(held, [b"\x00" * 16] * len(held))
    return HowlFile(spu_addrs=[SpuAddrEntry(0, 2) for _ in range(slots)], banks=[bank])


class TestSampleTargets:

    def test_marks_free_slots_but_keeps_every_slot_pickable(self, builder):
        choices = builder.sample_targets(_hwl(3, held=[1]))

        assert [(c.spu_index, c.free, c.enabled) for c in choices] == [
            (0, True, True), (1, False, True), (2, True, True),
        ]

    def test_labels_the_owning_bank(self, builder):
        choices = builder.sample_targets(_hwl(2, held=[1]))

        assert "Bank 0" in choices[1].display
        assert "Bank" not in choices[0].display


class TestNewSampleSlots:

    def test_only_free_slots_are_pickable(self, builder):
        choices = builder.new_sample_slots(_hwl(LIMIT, held=list(range(1, LIMIT))))

        assert [c.spu_index for c in choices if c.enabled] == [0]
        assert all(c.free for c in choices if c.enabled)

    def test_offers_a_new_slot_while_the_table_has_room(self, builder):
        choices = builder.new_sample_slots(_hwl(3, held=[0, 1, 2]))

        assert [c.spu_index for c in choices if c.enabled] == [3]

    def test_no_new_slot_once_the_table_is_full(self, builder):
        choices = builder.new_sample_slots(_hwl(LIMIT, held=list(range(LIMIT))))

        assert not any(c.enabled for c in choices)

    def test_share_option_comes_first_and_is_pickable(self, builder):
        choices = builder.new_sample_slots(_hwl(3, held=[0, 1, 2]), share_spu=1)

        assert (choices[0].spu_index, choices[0].enabled) == (1, True)
        assert "share" in choices[0].display

    def test_slots_past_the_stock_table_cannot_take_new_samples(self, builder):
        choices = builder.new_sample_slots(_hwl(LIMIT + 2, held=[]))
        past = [c for c in choices if c.spu_index >= LIMIT]

        assert past and not any(c.enabled for c in past)


class TestDefaultNewSlot:

    def test_prefers_sharing_when_offered(self, builder):
        assert builder.default_new_slot(_hwl(3, held=[0, 1, 2]), share_spu=2) == 2

    def test_otherwise_uses_the_allocator(self, builder):
        assert builder.default_new_slot(_hwl(LIMIT, held=list(range(1, LIMIT)))) == 0
