# coding: utf-8

import pytest

from howl_editor.ctr.analysis.sample_ownership import SampleOwnershipResolver
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.diagnostics.shared_sample_guard import SharedSampleGuard
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.ps1.formats.vag import format as fmt
from howl_editor.ps1.formats.vag.structure_validator import VagStructureValidator
from tests.conftest import build_bank_blob


def _vag(frames: int) -> bytes:
    """A well-formed one-shot: plain frames then a terminator."""
    body = b"".join(bytes([0x20, 0x00]) + b"\x11" * 14 for _ in range(frames - 1))
    return body + bytes([0x20, fmt.FLAG_LOOP_END]) + b"\x11" * 14


@pytest.fixture
def guard(bank_reader):
    ownership = SampleOwnershipResolver(bank_reader)
    slices = BankSliceValidator(bank_reader, VagStructureValidator())
    return SharedSampleGuard(ownership, slices, bank_reader)


def _hwl(bank_ids: list[list[int]], sizes: dict[int, int]) -> HowlFile:
    """sizes maps spu id -> frame count; every bank carries its own copy."""
    spu_addrs = [SpuAddrEntry(0, 0) for _ in range(max(sizes) + 1)]
    for sid, frames in sizes.items():
        spu_addrs[sid] = SpuAddrEntry(0, frames * fmt.FRAME_SIZE // 8)

    banks = [
        build_bank_blob(ids, [_vag(sizes[sid]) for sid in ids])
        for ids in bank_ids
    ]

    return HowlFile(spu_addrs=spu_addrs, banks=banks)


class TestUnshared:
    """A sample only one bank claims can be resized freely — nothing else is
    cut using its size entry."""

    def test_sample_in_one_bank_passes(self, guard):
        hwl = _hwl([[0, 1], [2]], {0: 4, 1: 4, 2: 4})

        check = guard.check(hwl, bank_index=0, spu_index=1, new_byte_size=16 * 9)

        assert check.within_limit
        assert check.impacts == []


class TestSharedSample:
    """The size table is keyed by sample id and shared by every claiming bank,
    while each bank holds its own bytes. Moving the entry re-cuts the others."""

    def test_resizing_a_shared_sample_is_flagged(self, guard):
        # id 1 lives in both banks; only bank 0 is being edited.
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})

        check = guard.check(hwl, bank_index=0, spu_index=1, new_byte_size=16 * 9)

        assert not check.within_limit
        assert check.other_banks == [1]
        assert check.old_byte_size == 16 * 4
        assert check.new_byte_size == 16 * 9

    def test_reports_how_many_slices_break(self, guard):
        # Growing id 1 pushes bank 1's later sample off its boundary too.
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})

        check = guard.check(hwl, bank_index=0, spu_index=1, new_byte_size=16 * 9)
        impact = check.impacts[0]

        assert impact.bank_index == 1
        assert impact.sample_count == 2
        assert impact.bad_slices > 0

    def test_same_size_replacement_passes(self, guard):
        """Swapping in a sample of identical length leaves the size entry put,
        so the other banks keep slicing correctly."""
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})

        check = guard.check(hwl, bank_index=0, spu_index=1, new_byte_size=16 * 4)

        assert check.within_limit
        assert check.impacts == []

    def test_every_other_owner_is_reported(self, guard):
        hwl = _hwl([[1], [1], [1], [2]], {1: 4, 2: 4})

        check = guard.check(hwl, bank_index=0, spu_index=1, new_byte_size=16 * 9)

        assert check.other_banks == [1, 2]
