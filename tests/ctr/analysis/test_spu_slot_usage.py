# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.analysis.spu_slot_usage import SpuSlotUsageResolver
from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.howl.models import EngineFX, HowlFile, OtherFX, SpuAddrEntry
from tests.conftest import build_bank_blob, build_cseq_bytes


@pytest.fixture
def usage(bank_reader, cseq_reader):
    return SpuSlotUsageResolver(bank_reader, cseq_reader)


def _hwl(slots: int, **kwargs) -> HowlFile:
    return HowlFile(spu_addrs=[SpuAddrEntry(0, 2) for _ in range(slots)], **kwargs)


class TestFreeSlots:

    def test_unreferenced_slots_are_free(self, usage):
        assert usage.free_slots(_hwl(3)) == {0, 1, 2}

    def test_slot_in_a_bank_is_used(self, usage):
        hwl = _hwl(3, banks=[build_bank_blob([1], [b"\x00" * 16])])

        assert usage.free_slots(hwl) == {0, 2}

    def test_slot_played_by_other_fx_is_used(self, usage):
        hwl = _hwl(3, other_fx=[OtherFX(spu_index=0)])

        assert usage.free_slots(hwl) == {1, 2}

    def test_slot_played_by_engine_fx_is_used(self, usage):
        hwl = _hwl(3, engine_fx=[EngineFX(spu_index=2)])

        assert usage.free_slots(hwl) == {0, 1}

    def test_slots_a_song_points_at_are_used_even_without_a_bank(self, usage):
        # A song pointing at an empty slot would suddenly play the new sample.
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=0)],
            percussions=[CseqPercussion(sample_id=2)],
        )

        assert usage.free_slots(_hwl(3, songs=[song])) == {1}

    def test_slots_past_the_stock_table_are_never_free(self, usage):
        free = usage.free_slots(_hwl(constants.MAX_SPU_SLOTS + 4))

        assert max(free) == constants.MAX_SPU_SLOTS - 1

    def test_unreadable_song_does_not_block_everything(self, usage):
        assert usage.free_slots(_hwl(2, songs=[b"\xFF"])) == {0, 1}
