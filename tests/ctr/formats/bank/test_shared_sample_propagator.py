# coding: utf-8

import pytest

from howl_editor.ctr.analysis.sample_ownership import SampleOwnershipResolver
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.formats.bank.shared_sample_propagator import SharedSamplePropagator
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.ps1.formats.vag import format as fmt
from howl_editor.ps1.formats.vag.structure_validator import VagStructureValidator
from tests.conftest import build_bank_blob


def _vag(frames: int, filler: int = 0x11) -> bytes:
    body = b"".join(bytes([0x20, 0x00]) + bytes([filler]) * 14 for _ in range(frames - 1))
    return body + bytes([0x20, fmt.FLAG_LOOP_END]) + bytes([filler]) * 14


@pytest.fixture
def propagator(bank_reader, bank_builder):
    return SharedSamplePropagator(
        bank_reader, bank_builder, SampleOwnershipResolver(bank_reader),
    )


def _hwl(bank_ids: list[list[int]], frames: dict[int, int]) -> HowlFile:
    spu_addrs = [SpuAddrEntry(0, 0) for _ in range(max(frames) + 1)]
    for sid, n in frames.items():
        spu_addrs[sid] = SpuAddrEntry(0, n * fmt.FRAME_SIZE // 8)

    banks = [build_bank_blob(ids, [_vag(frames[s]) for s in ids]) for ids in bank_ids]
    return HowlFile(spu_addrs=spu_addrs, banks=banks)


class TestRebuildOwners:

    def test_returns_a_blob_for_each_other_owner(self, propagator):
        hwl = _hwl([[0, 1], [1, 2], [3]], {0: 4, 1: 4, 2: 4, 3: 4})

        out = propagator.rebuild_owners(
            hwl, list(hwl.spu_addrs), spu_index=1, new_data=_vag(9), exclude_bank=0,
        )

        assert list(out) == [1]

    def test_edited_bank_is_excluded(self, propagator):
        hwl = _hwl([[1], [1]], {1: 4})

        out = propagator.rebuild_owners(
            hwl, list(hwl.spu_addrs), spu_index=1, new_data=_vag(9), exclude_bank=1,
        )

        assert list(out) == [0]

    def test_unshared_sample_needs_no_companions(self, propagator):
        hwl = _hwl([[0, 1], [2]], {0: 4, 1: 4, 2: 4})

        out = propagator.rebuild_owners(
            hwl, list(hwl.spu_addrs), spu_index=1, new_data=_vag(9), exclude_bank=0,
        )

        assert out == {}

    def test_rebuilt_bank_slices_cleanly_under_the_new_size(
        self, propagator, bank_reader,
    ):
        """The point of propagating: after the size entry moves, the companion
        bank must still parse into valid samples."""
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})
        new_data = _vag(9, filler=0x22)

        out = propagator.rebuild_owners(
            hwl, list(hwl.spu_addrs), spu_index=1, new_data=new_data, exclude_bank=0,
        )

        # Install the size this replacement would set, then re-slice bank 1.
        after = list(hwl.spu_addrs)
        after[1] = SpuAddrEntry(0, len(new_data) // 8)
        validator = BankSliceValidator(bank_reader, VagStructureValidator())

        assert validator.validate(out[1], after).is_valid

    def test_untouched_bank_breaks_without_propagation(
        self, propagator, bank_reader,
    ):
        """The bug this exists to prevent: leave the companion alone and the
        new size cuts it at offsets its bytes no longer match."""
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})

        after = list(hwl.spu_addrs)
        after[1] = SpuAddrEntry(0, len(_vag(9)) // 8)
        validator = BankSliceValidator(bank_reader, VagStructureValidator())

        assert not validator.validate(hwl.banks[1], after).is_valid

    def test_carries_the_replacement_into_the_companion(self, propagator, bank_reader):
        hwl = _hwl([[0, 1], [1, 2]], {0: 4, 1: 4, 2: 4})
        new_data = _vag(9, filler=0x22)

        out = propagator.rebuild_owners(
            hwl, list(hwl.spu_addrs), spu_index=1, new_data=new_data, exclude_bank=0,
        )

        after = list(hwl.spu_addrs)
        after[1] = SpuAddrEntry(0, len(new_data) // 8)
        rebuilt = {s.spu_index: s.data for s in bank_reader.parse(out[1], after)}

        assert rebuilt[1] == new_data
