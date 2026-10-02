# coding: utf-8

import pytest

from howl_editor.core.blob_cache import BlobCache
from howl_editor.ctr.analysis.sample_ownership import SampleOwnershipResolver
from howl_editor.ctr.analysis.sample_replacement_planner import SampleReplacementPlanner
from howl_editor.ctr.diagnostics.bank_size_guard import BankSizeGuard
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.diagnostics.shared_sample_guard import SharedSampleGuard
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.ps1.formats.vag.structure_validator import VagStructureValidator
from tests.conftest import build_bank_blob

SAMPLE = b"\x00" * 32   # 4 SPU units


@pytest.fixture
def planner(bank_reader, bank_builder, stock_layout):
    ownership = SampleOwnershipResolver(bank_reader)
    slices = BankSliceValidator(bank_reader, VagStructureValidator(), BlobCache())

    return SampleReplacementPlanner(
        bank_reader, bank_builder,
        SharedSampleGuard(ownership, slices, bank_reader),
        BankSizeGuard(SpuResidencyCalculator(bank_reader), stock_layout),
    )


def _hwl(shared: bool = False) -> HowlFile:
    """Bank 1 holds slots 0 and 2; with `shared`, bank 2 also holds slot 0."""
    spu = [SpuAddrEntry(0, 4) for _ in range(4)]
    banks = [
        build_bank_blob([], []),
        build_bank_blob([0, 2], [SAMPLE, SAMPLE]),
    ]

    if shared:
        banks.append(build_bank_blob([0], [SAMPLE]))

    return HowlFile(spu_addrs=spu, banks=banks)


class TestPlan:

    def test_reports_the_slot_and_both_sizes(self, planner):
        plan = planner.plan(_hwl(), 1, 0, b"\x11" * 64)

        assert plan.spu_index == 0
        assert (plan.old_byte_size, plan.new_byte_size) == (32, 64)
        assert plan.size_delta == 32

    def test_a_smaller_sample_reports_a_negative_delta(self, planner):
        plan = planner.plan(_hwl(), 1, 0, b"\x11" * 16)

        assert plan.size_delta == -16

    def test_builds_the_prospective_bank_without_touching_the_file(self, planner):
        hwl = _hwl()
        sizes_before = [e.size for e in hwl.spu_addrs]
        original_blob = hwl.banks[1]

        plan = planner.plan(hwl, 1, 0, b"\x11" * 64)

        assert plan.new_blob != original_blob
        assert hwl.banks[1] == original_blob
        assert [e.size for e in hwl.spu_addrs] == sizes_before

    def test_rejects_a_sample_index_that_is_not_there(self, planner):
        with pytest.raises(IndexError):
            planner.plan(_hwl(), 1, 9, SAMPLE)


class TestSharedSlots:

    def test_a_resize_of_a_shared_slot_needs_a_choice(self, planner):
        plan = planner.plan(_hwl(shared=True), 1, 0, b"\x11" * 64)

        assert plan.needs_shared_choice is True
        assert plan.shared_banks == [2]

    def test_a_same_size_replacement_leaves_other_banks_alone(self, planner):
        plan = planner.plan(_hwl(shared=True), 1, 0, b"\x11" * 32)

        assert plan.needs_shared_choice is False

    def test_a_slot_no_one_else_holds_needs_no_choice(self, planner):
        plan = planner.plan(_hwl(), 1, 0, b"\x11" * 64)

        assert plan.needs_shared_choice is False


class TestBankBudget:

    def test_a_modest_replacement_stays_within_the_budget(self, planner):
        plan = planner.plan(_hwl(), 1, 0, b"\x11" * 64)

        assert plan.exceeds_bank_limit is False

    def test_an_enormous_sample_reports_the_overflow(self, planner):
        plan = planner.plan(_hwl(), 1, 0, b"\x11" * (600 * 1024))

        assert plan.exceeds_bank_limit is True
        assert plan.bank_size.warning_text
