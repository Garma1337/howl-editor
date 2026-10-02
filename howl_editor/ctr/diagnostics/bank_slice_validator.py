# coding: utf-8

from dataclasses import dataclass, field
from struct import pack

from howl_editor.core.blob_cache import BlobCache
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import SpuAddrEntry
from howl_editor.ps1.formats.vag.structure_validator import (
    VagStructureResult, VagStructureValidator,
)


@dataclass(frozen=True)
class BadSlice:
    slot: int
    spu_index: int
    structure: VagStructureResult


@dataclass(frozen=True)
class BankSliceResult:
    """Which of a bank's samples come out of the blob mis-cut.

    `declared_count` is what the bank's header claims to hold; `sample_count`
    is what actually came back. They diverge when the sizes overrun the blob,
    because the reader drops the samples that no longer fit — so a bank can be
    damaged without producing a single bad slice to look at."""

    declared_count: int = 0
    sample_count: int = 0
    bad_slices: list[BadSlice] = field(default_factory=list)

    @property
    def dropped_count(self) -> int:
        return max(0, self.declared_count - self.sample_count)

    @property
    def corrupted_count(self) -> int:
        return len(self.bad_slices) + self.dropped_count

    @property
    def is_valid(self) -> bool:
        return self.corrupted_count == 0

    @property
    def first_bad(self) -> BadSlice | None:
        return self.bad_slices[0] if self.bad_slices else None


class BankSliceValidator:
    """Detects banks whose sample boundaries disagree with the SPU size table.

    A bank blob is bare concatenated VAG data — the only thing saying where one
    sample stops and the next starts is ``spu_addrs[id].size``, which is global
    and shared by every bank using that id. Resize a sample in one bank and any
    other bank holding the same id keeps its old bytes while being cut with the
    new size, so every sample from that id onward is read at the wrong offset.

    The engine has the same exposure: it derives each sample's SPU address by
    walking those sizes and then uploads the blob as one block, so a mismatch is
    already wrong on the very first upload — no cross-bank RAM reuse needed.
    Misalignment is detectable because the slices stop being valid VAG."""

    def __init__(
        self, bank_reader: BankReader, structure: VagStructureValidator, blob_cache: BlobCache,
    ):
        self._bank_reader = bank_reader
        self._structure = structure
        self._cache = blob_cache

    def validate(self, bank_blob: bytes, spu_addrs: list[SpuAddrEntry]) -> BankSliceResult:
        """Cached: decoding every sample's VAG structure is the slowest check
        in the file sweep, and it only changes when the bank or the size table
        does. The result is shared, so treat it as read-only."""
        return self._cache.get(
            bank_blob, lambda blob: self._validate(blob, spu_addrs), self._sizes_salt(spu_addrs),
        )

    def _sizes_salt(self, spu_addrs: list[SpuAddrEntry]) -> bytes:
        return pack(f"<{len(spu_addrs)}H", *(e.size for e in spu_addrs))

    def _validate(self, bank_blob: bytes, spu_addrs: list[SpuAddrEntry]) -> BankSliceResult:
        declared = self._bank_reader.sample_ids(bank_blob)
        samples = self._bank_reader.parse(bank_blob, spu_addrs)
        bad: list[BadSlice] = []

        for slot, sample in enumerate(samples):
            result = self._structure.validate(sample.data)

            if not result.is_valid:
                bad.append(BadSlice(slot=slot, spu_index=sample.spu_index, structure=result))

        return BankSliceResult(
            declared_count=len(declared),
            sample_count=len(samples),
            bad_slices=bad,
        )
