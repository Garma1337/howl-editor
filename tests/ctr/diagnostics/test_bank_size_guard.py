# coding: utf-8

from howl_editor.ctr import constants, stock_layout as layout
from howl_editor.ctr.diagnostics.bank_size_guard import BankSizeGuard
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.analysis.stock_layout_resolver import StockLayoutResolver
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from tests.conftest import build_bank_blob


def _guard(bank_reader) -> BankSizeGuard:
    return BankSizeGuard(SpuResidencyCalculator(bank_reader), StockLayoutResolver())


def _units(byte_len: int) -> int:
    return byte_len // 8


class TestBankSizeGuard:

    def _hwl_with_level_bank(self, sample_bytes: int) -> tuple[HowlFile, bytes]:
        """A file whose bank 1 (a level FX bank) holds one sample of the given
        size, plus a small bank 0. Returns the file and bank 1's blob."""
        hwl = HowlFile()
        # sample 0 -> bank 0 (tiny), sample 1 -> bank 1 (sized)
        hwl.spu_addrs = [SpuAddrEntry(0, _units(2048)), SpuAddrEntry(0, _units(sample_bytes))]
        bank0 = build_bank_blob([0], [b"\x00" * 2048])
        bank1 = build_bank_blob([1], [b"\x00" * sample_bytes])
        hwl.banks = [bank0, bank1]
        return hwl, bank1

    def test_within_limit_for_small_level_bank(self, bank_reader):
        hwl, bank1 = self._hwl_with_level_bank(64 * 1024)

        check = _guard(bank_reader).check(hwl, 1, bank1)

        assert check.within_limit is True
        assert check.warning_text == ""
        # Level bank 1's assumed context includes bank 0 and the 8-driver bank.
        assert layout.SFX_UNIVERSAL_BANK in check.resident_banks

    def test_warns_when_prospective_blob_busts_the_budget(self, bank_reader):
        hwl, _ = self._hwl_with_level_bank(64 * 1024)

        # A prospective bank 1 whose single sample alone exceeds the SPU budget.
        big_bytes = constants.SPU_USABLE_SAMPLE_BYTES + 8192
        hwl.spu_addrs[1] = SpuAddrEntry(0, _units(big_bytes))
        big_blob = build_bank_blob([1], [b"\x00" * big_bytes])

        check = _guard(bank_reader).check(hwl, 1, big_blob)

        assert check.within_limit is False
        assert check.over_by > 0
        assert check.warning_text != ""

    def test_custom_bank_uses_minimal_context(self, bank_reader):
        hwl, _ = self._hwl_with_level_bank(64 * 1024)
        # Pad the bank list so a custom-range index exists.
        while len(hwl.banks) <= layout.FIRST_CUSTOM_BANK:
            hwl.banks.append(build_bank_blob([0], [b"\x00" * 8]))
        custom_index = layout.FIRST_CUSTOM_BANK
        blob = build_bank_blob([0], [b"\x00" * 8])

        check = _guard(bank_reader).check(hwl, custom_index, blob)

        # Minimal set: bank 0 + the custom bank itself.
        assert set(check.resident_banks) == {layout.SFX_UNIVERSAL_BANK, custom_index}
