# coding: utf-8

from howl_editor.ctr import constants
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.formats.howl.models import SpuAddrEntry
from tests.conftest import build_bank_blob


def _calc(bank_reader) -> SpuResidencyCalculator:
    return SpuResidencyCalculator(bank_reader)


def _spu_addrs(sizes_in_units: list[int]) -> list[SpuAddrEntry]:
    # SpuAddrEntry.byte_size == size * 8, so pass sizes in 8-byte units.
    return [SpuAddrEntry(ptr=0, size=s) for s in sizes_in_units]


class TestResidency:

    def test_sums_unique_sample_bytes(self, bank_reader):
        spu_addrs = _spu_addrs([100, 200, 300])   # byte sizes 800, 1600, 2400
        bank = build_bank_blob([0, 1, 2], [b"\x00" * 800, b"\x00" * 1600, b"\x00" * 2400])

        res = _calc(bank_reader).residency(spu_addrs, {5: bank})

        assert res.sample_ids == frozenset({0, 1, 2})
        assert res.total_bytes == 800 + 1600 + 2400
        assert res.bank_count == 1

    def test_shared_sample_counted_once(self, bank_reader):
        spu_addrs = _spu_addrs([100, 100, 100])   # each 800 bytes
        # Two banks that both reference sample id 1.
        bank_a = build_bank_blob([0, 1], [b"\x00" * 800, b"\x00" * 800])
        bank_b = build_bank_blob([1, 2], [b"\x00" * 800, b"\x00" * 800])

        res = _calc(bank_reader).residency(spu_addrs, {0: bank_a, 4: bank_b})

        assert res.sample_ids == frozenset({0, 1, 2})
        assert res.total_bytes == 3 * 800   # not 4 * 800 — id 1 deduped
        assert res.bank_count == 2

    def test_fits_just_under_ceiling(self, bank_reader):
        # One sample sized so heap_start + total == ceiling - 8 (still below).
        target = constants.SPU_SAMPLE_CEILING - constants.SPU_HEAP_START - 8
        units = target // 8
        spu_addrs = _spu_addrs([units])
        bank = build_bank_blob([0], [b"\x00" * (units * 8)])

        res = _calc(bank_reader).residency(spu_addrs, {1: bank})

        assert res.fits is True
        assert res.over_by == 0

    def test_over_ceiling_reports_overflow(self, bank_reader):
        # Push the end address past the ceiling.
        target = constants.SPU_SAMPLE_CEILING - constants.SPU_HEAP_START + 800
        units = target // 8
        spu_addrs = _spu_addrs([units])
        bank = build_bank_blob([0], [b"\x00" * (units * 8)])

        res = _calc(bank_reader).residency(spu_addrs, {1: bank})

        assert res.fits is False
        assert res.over_by == constants.SPU_HEAP_START + units * 8 - constants.SPU_SAMPLE_CEILING

    def test_too_many_banks(self, bank_reader):
        spu_addrs = _spu_addrs([1] * 4)
        blobs = {i: build_bank_blob([0], [b"\x00" * 8]) for i in range(9)}

        res = _calc(bank_reader).residency(spu_addrs, blobs)

        assert res.bank_count == 9
        assert res.too_many_banks is True

    def test_eight_banks_is_not_too_many(self, bank_reader):
        spu_addrs = _spu_addrs([1])
        blobs = {i: build_bank_blob([0], [b"\x00" * 8]) for i in range(8)}

        res = _calc(bank_reader).residency(spu_addrs, blobs)

        assert res.too_many_banks is False
