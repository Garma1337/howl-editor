# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr import constants
from howl_editor.ctr import stock_layout as layout
from howl_editor.ctr.diagnostics.spu_residency import SpuResidencyCalculator
from howl_editor.ctr.analysis.stock_layout_resolver import StockLayoutResolver
from howl_editor.ctr.formats.howl.models import HowlFile


@dataclass(frozen=True)
class BankSizeCheck:
    within_limit: bool
    total_bytes: int
    ceiling: int
    over_by: int
    resident_banks: tuple[int, ...]   # the co-resident set the estimate assumed
    warning_text: str


class BankSizeGuard:
    """Checks whether editing a bank keeps its worst-case race — the banks
    resident in SPU RAM together — within the console's sample budget.

    Residency is context-dependent (which character banks load varies by mode),
    so the check assembles a representative worst-case co-resident set for the
    edited bank and evaluates it against the SPU ceiling. It is deliberately a
    warning, not a hard block: stock banks already sit well under the ceiling,
    so it only fires when an edit genuinely bloats a bank.
    """

    def __init__(
        self,
        residency: SpuResidencyCalculator,
        stock_layout: StockLayoutResolver,
    ):
        self._residency = residency
        self._layout = stock_layout

    def check(self, hwl: HowlFile, bank_index: int, new_blob: bytes) -> BankSizeCheck:
        blobs = {i: blob for i, blob in enumerate(hwl.banks)}
        blobs[bank_index] = new_blob   # evaluate the prospective, not-yet-applied edit

        context = self._context_indices(hwl, bank_index, blobs)
        ctx_blobs = {i: blobs[i] for i in context if i in blobs}
        res = self._residency.residency(hwl.spu_addrs, ctx_blobs)

        within = res.fits and not res.too_many_banks
        resident = tuple(sorted(ctx_blobs))

        text = "" if within else (
            f"After this change the sounds a race loads together "
            f"(banks {', '.join(str(i) for i in resident)}) total {res.total_bytes} "
            f"bytes of SPU RAM — {res.over_by} over the {constants.SPU_USABLE_SAMPLE_BYTES}-"
            f"byte limit the console has for all loaded samples. The game skips "
            f"samples that don't fit, so some sounds go silent in game. Reduce the "
            f"bank's sample sizes or count.\n\nSave it anyway?"
        )

        return BankSizeCheck(
            within_limit=within,
            total_bytes=res.total_bytes,
            ceiling=constants.SPU_USABLE_SAMPLE_BYTES,
            over_by=res.over_by,
            resident_banks=resident,
            warning_text=text,
        )

    def _context_indices(
        self, hwl: HowlFile, bank_index: int, blobs: dict[int, bytes],
    ) -> set[int]:
        """The banks that plausibly share SPU RAM with `bank_index` in its
        heaviest realistic context. Bank 0 (universal SFX) is normally resident,
        but the two isolated special levels destroy it, so they load alone."""
        if self._layout.loads_in_isolation(bank_index):
            # Intro Race / Naughty Dog Crate load only this bank — nothing else.
            return {bank_index}

        base = {layout.SFX_UNIVERSAL_BANK, bank_index}

        if bank_index == layout.SFX_UNIVERSAL_BANK:
            # Bank 0 co-resides with a race track and the 8-driver shared bank.
            return base | {layout.EIGHT_DRIVER_SHARED_BANK,
                           self._largest_race_bank(hwl, blobs)}

        if self._layout.is_custom_bank(bank_index):
            # Unknown role — the minimal always-true set (bank 0 + this bank).
            return base

        if (self._layout.is_character_bank(bank_index)
                or self._layout.is_podium_bank(bank_index)):
            # A small character/podium bank rides on top of a level bank.
            return base | {self._largest_race_bank(hwl, blobs)}

        if self._layout.is_race_track_bank(bank_index):
            # A race track loads the 8-driver shared bank in a full grid.
            return base | {layout.EIGHT_DRIVER_SHARED_BANK}

        # Arena / boss / menu / ending banks: bank 0 + this bank; no 8-driver bank.
        return base

    def _largest_race_bank(self, hwl: HowlFile, blobs: dict[int, bytes]) -> int | None:
        """The race-track FX bank with the biggest SPU footprint — the worst case
        to pair a character/podium bank (or bank 0) against, since those are what
        co-load the 8-driver-eligible race banks."""
        best_index: int | None = None
        best_bytes = -1

        for i in range(len(hwl.banks)):
            if not self._layout.is_race_track_bank(i):
                continue

            footprint = self._residency.residency(hwl.spu_addrs, {i: blobs[i]}).total_bytes
            if footprint > best_bytes:
                best_bytes = footprint
                best_index = i

        return best_index
