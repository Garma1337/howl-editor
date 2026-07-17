# coding: utf-8

from dataclasses import dataclass, field

from howl_editor.ctr.analysis.sample_ownership import SampleOwnershipResolver
from howl_editor.ctr.diagnostics.bank_slice_validator import BankSliceValidator
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry


@dataclass(frozen=True)
class BankImpact:
    """How badly one other bank would be cut up by the resize."""
    bank_index: int
    bank_name: str
    bad_slices: int
    sample_count: int


@dataclass(frozen=True)
class SharedSampleCheck:
    within_limit: bool
    spu_index: int
    old_byte_size: int
    new_byte_size: int
    impacts: list[BankImpact] = field(default_factory=list)
    warning_text: str = ""

    @property
    def other_banks(self) -> list[int]:
        return [i.bank_index for i in self.impacts]


class SharedSampleGuard:
    """Warns before a sample replacement silently mis-cuts other banks.

    Sample sizes live in one global table keyed by SPU id, but each bank that
    claims an id carries its own copy of the bytes. Writing a different-sized
    sample updates the shared size entry while rebuilding only the edited
    bank, so every other claiming bank is left being sliced with a size its
    blob no longer matches — corrupting it from that sample onward, with no
    error at save time and no way to tell from the edited bank.

    Replacing a sample with one of exactly the same length is safe: the size
    entry does not move, so the other banks keep slicing correctly (they just
    keep their own, now-different, audio for that id)."""

    def __init__(
        self,
        ownership: SampleOwnershipResolver,
        slice_validator: BankSliceValidator,
        bank_reader: BankReader,
    ):
        self._ownership = ownership
        self._slices = slice_validator
        self._bank_reader = bank_reader

    def check(
        self, hwl: HowlFile, bank_index: int, spu_index: int, new_byte_size: int,
    ) -> SharedSampleCheck:
        old = self._old_size(hwl, spu_index)
        others = self._ownership.other_owners(hwl, spu_index, bank_index)

        if not others or new_byte_size == old:
            return SharedSampleCheck(
                within_limit=True,
                spu_index=spu_index,
                old_byte_size=old,
                new_byte_size=new_byte_size,
            )

        impacts = self._impacts(hwl, spu_index, new_byte_size, others)

        return SharedSampleCheck(
            within_limit=False,
            spu_index=spu_index,
            old_byte_size=old,
            new_byte_size=new_byte_size,
            impacts=impacts,
            warning_text=self._describe(spu_index, old, new_byte_size, impacts),
        )

    def _old_size(self, hwl: HowlFile, spu_index: int) -> int:
        if 0 <= spu_index < len(hwl.spu_addrs):
            return hwl.spu_addrs[spu_index].byte_size

        return 0

    def _impacts(
        self, hwl: HowlFile, spu_index: int, new_byte_size: int, others: list[int],
    ) -> list[BankImpact]:
        """Re-slice each other bank against the size this edit would install,
        so the warning can report real counts rather than a vague caution."""
        probe = list(hwl.spu_addrs)
        probe[spu_index] = SpuAddrEntry(0, new_byte_size // 8)
        out: list[BankImpact] = []

        for bank_index in others:
            result = self._slices.validate(hwl.banks[bank_index], probe)
            out.append(BankImpact(
                bank_index=bank_index,
                bank_name=self._bank_reader.get_name(bank_index),
                bad_slices=result.corrupted_count,
                sample_count=result.declared_count,
            ))

        return out

    def _describe(
        self, spu_index: int, old: int, new: int, impacts: list[BankImpact],
    ) -> str:
        lines = [
            f"SPU {spu_index} is also used by {self._bank_phrase(len(impacts))}.",
            "",
            f"Its size is shared by every bank that uses it, so resizing it "
            f"({old} → {new} bytes) re-cuts their samples too:",
            "",
        ]

        for impact in impacts:
            lines.append(
                f"  • Bank {impact.bank_index} ({impact.bank_name}): "
                f"{impact.bad_slices} of {impact.sample_count} samples would be corrupted",
            )

        return "\n".join(lines)

    def _bank_phrase(self, count: int) -> str:
        return "another bank" if count == 1 else f"{count} other banks"
