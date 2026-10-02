# coding: utf-8

import pytest

from howl_editor.ctr import constants
from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.saphi.formats.sca.spu_slot_validator import ScaSpuSlotValidator
from tests.conftest import build_bank_blob, build_cseq_bytes

LIMIT = constants.MAX_SPU_SLOTS


@pytest.fixture
def validator(bank_reader, cseq_reader, spu_slot_guard):
    return ScaSpuSlotValidator(bank_reader, cseq_reader, spu_slot_guard)


class TestOutOfRangeSlots:

    def test_stock_slots_pass(self, validator):
        bank = build_bank_blob([3, LIMIT - 1], [b"\x00" * 16, b"\x00" * 16])
        cseq = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=3)],
            percussions=[CseqPercussion(sample_id=LIMIT - 1)],
        )

        assert validator.out_of_range_slots(bank, cseq) == []

    def test_reports_bank_samples_past_the_table(self, validator):
        bank = build_bank_blob([3, LIMIT + 1, LIMIT], [b"\x00" * 16] * 3)

        assert validator.out_of_range_slots(bank, build_cseq_bytes()) == [LIMIT, LIMIT + 1]

    def test_reports_song_references_missing_from_the_bank(self, validator):
        bank = build_bank_blob([3], [b"\x00" * 16])
        cseq = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=LIMIT + 4)],
            percussions=[CseqPercussion(sample_id=LIMIT + 2)],
        )

        assert validator.out_of_range_slots(bank, cseq) == [LIMIT + 2, LIMIT + 4]
