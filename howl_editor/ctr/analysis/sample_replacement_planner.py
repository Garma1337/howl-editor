# coding: utf-8

from dataclasses import dataclass, field, replace

from howl_editor.ctr.diagnostics.bank_size_guard import BankSizeCheck, BankSizeGuard
from howl_editor.ctr.diagnostics.shared_sample_guard import BankImpact, SharedSampleGuard
from howl_editor.ctr.formats.bank.builder import BankBuilder
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry


@dataclass(frozen=True)
class SampleReplacementPlan:
    """Everything replacing one sample would do, worked out up front."""

    bank_index: int
    sample_index: int
    spu_index: int | None
    old_byte_size: int
    new_byte_size: int
    new_blob: bytes
    shared_impacts: list[BankImpact] = field(default_factory=list)
    bank_size: BankSizeCheck | None = None

    @property
    def size_delta(self) -> int:
        return self.new_byte_size - self.old_byte_size

    @property
    def shared_banks(self) -> list[int]:
        return [impact.bank_index for impact in self.shared_impacts]

    @property
    def needs_shared_choice(self) -> bool:
        """Whether other banks would be left mis-cut unless they are rebuilt."""
        return bool(self.shared_impacts)

    @property
    def exceeds_bank_limit(self) -> bool:
        return self.bank_size is not None and not self.bank_size.within_limit


class SampleReplacementPlanner:
    """Dry-runs a sample replacement.

    The write path mutates the SPU size table in place, so every question the
    user has to answer — size change, other banks claiming the same slot, the
    resulting SPU footprint — can only be answered after the fact unless it is
    simulated first. This simulates it against copies and reports."""

    def __init__(
        self,
        bank_reader: BankReader,
        bank_builder: BankBuilder,
        shared_guard: SharedSampleGuard,
        bank_size_guard: BankSizeGuard,
    ):
        self._bank_reader = bank_reader
        self._bank_builder = bank_builder
        self._shared_guard = shared_guard
        self._bank_size_guard = bank_size_guard

    def plan(
        self, hwl: HowlFile, bank_index: int, sample_index: int, new_data: bytes,
    ) -> SampleReplacementPlan:
        samples = self._bank_reader.parse(hwl.banks[bank_index], hwl.spu_addrs)

        if sample_index < 0 or sample_index >= len(samples):
            raise IndexError(f"Sample index {sample_index} out of range")

        sample = samples[sample_index]
        probe = [SpuAddrEntry(e.ptr, e.size) for e in hwl.spu_addrs]
        new_blob = self._bank_builder.replace_sample(
            hwl.banks[bank_index], probe, sample_index, new_data, self._bank_reader,
        )
        # The SPU footprint has to be judged against the sizes this edit would
        # write, not the ones still in the file, or a bloated sample looks free.
        prospective = replace(hwl, spu_addrs=probe)

        return SampleReplacementPlan(
            bank_index=bank_index,
            sample_index=sample_index,
            spu_index=sample.spu_index,
            old_byte_size=len(sample.data),
            new_byte_size=len(new_data),
            new_blob=new_blob,
            shared_impacts=self._shared_impacts(hwl, bank_index, sample.spu_index, len(new_data)),
            bank_size=self._bank_size_guard.check(prospective, bank_index, new_blob),
        )

    def _shared_impacts(
        self, hwl: HowlFile, bank_index: int, spu_index: int, new_byte_size: int,
    ) -> list[BankImpact]:
        check = self._shared_guard.check(hwl, bank_index, spu_index, new_byte_size)

        return [] if check.within_limit else list(check.impacts)
