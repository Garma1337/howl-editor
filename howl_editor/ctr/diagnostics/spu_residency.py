# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr import constants
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import SpuAddrEntry


@dataclass(frozen=True)
class Residency:
    """The SPU-RAM footprint of a set of banks resident together, modelling the
    engine's deduplication: a sample shared by several banks is uploaded once."""

    sample_ids: frozenset[int]
    total_bytes: int            # sum of each unique sample's byte_size
    bank_count: int
    fits: bool                  # heap start + total stays below the SPU ceiling
    over_by: int                # bytes past the ceiling (0 when it fits)
    too_many_banks: bool        # more banks than the engine keeps resident


class SpuResidencyCalculator:
    """Computes how much SPU sample RAM a group of banks needs when loaded at
    the same time.

    The CTR engine uploads each bank's samples once, skipping any whose
    ``spuAddr`` is already set (dedup by sample index), and every resident
    sample must end below ``SPU_SAMPLE_CEILING`` starting from ``SPU_HEAP_START``
    (see `howl_editor.ps1.spu`). This mirrors that: it unions the sample IDs the
    banks reference and sums each unique sample's ``byte_size`` once.
    """

    def __init__(self, bank_reader: BankReader):
        self._bank_reader = bank_reader

    def residency(
        self,
        spu_addrs: list[SpuAddrEntry],
        bank_blobs: dict[int, bytes],
    ) -> Residency:
        """``bank_blobs`` maps bank index → blob. Passing a not-yet-committed
        blob for the bank under edit lets callers check a prospective change
        before applying it. Bank indices are only used for the resident-bank
        count; sample dedup is purely by sample id."""
        sample_ids: set[int] = set()

        for blob in bank_blobs.values():
            for sample in self._bank_reader.parse(blob, spu_addrs):
                sample_ids.add(sample.spu_index)

        total_bytes = sum(spu_addrs[sid].byte_size for sid in sample_ids)
        end_addr = constants.SPU_HEAP_START + total_bytes
        over_by = max(0, end_addr - constants.SPU_SAMPLE_CEILING)

        return Residency(
            sample_ids=frozenset(sample_ids),
            total_bytes=total_bytes,
            bank_count=len(bank_blobs),
            fits=end_addr < constants.SPU_SAMPLE_CEILING,
            over_by=over_by,
            too_many_banks=len(bank_blobs) > constants.MAX_RESIDENT_BANKS,
        )
