# coding: utf-8

from howl_editor.ctr.analysis.sample_ownership import SampleOwnershipResolver
from howl_editor.ctr.formats.bank.builder import BankBuilder
from howl_editor.ctr.formats.bank.models import BankSample
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry


class SharedSamplePropagator:
    """Rebuilds the other banks that claim a sample so a resize stays coherent.

    A sample's size lives in one table shared by every bank claiming its id, so
    changing it obliges every claiming bank to carry bytes of that new length.
    Rebuilding them with the replacement keeps the file readable; leaving them
    alone leaves them cut at offsets their blobs no longer match.

    The engine only ever uploads one copy of a shared id anyway — whichever
    bank loads first wins — so the divergent copies this collapses were never
    all reachable to begin with."""

    def __init__(
        self,
        bank_reader: BankReader,
        bank_builder: BankBuilder,
        ownership: SampleOwnershipResolver,
    ):
        self._bank_reader = bank_reader
        self._bank_builder = bank_builder
        self._ownership = ownership

    def rebuild_owners(
        self,
        hwl: HowlFile,
        spu_addrs_before: list[SpuAddrEntry],
        spu_index: int,
        new_data: bytes,
        exclude_bank: int,
    ) -> dict[int, bytes]:
        """Bank index → rebuilt blob, for every bank other than `exclude_bank`
        claiming `spu_index`.

        `spu_addrs_before` must be the size table as it stood *before* the new
        size was installed: these banks still hold their original bytes, so
        cutting them with the new size would mis-parse the very data being
        repaired."""
        out: dict[int, bytes] = {}

        for bank_index in self._ownership.other_owners(hwl, spu_index, exclude_bank):
            samples = self._bank_reader.parse(hwl.banks[bank_index], spu_addrs_before)
            out[bank_index] = self._bank_builder.merge(
                self._swap(samples, spu_index, new_data),
            )

        return out

    def _swap(
        self, samples: list[BankSample], spu_index: int, new_data: bytes,
    ) -> list[BankSample]:
        return [
            BankSample(spu_index=s.spu_index, data=new_data)
            if s.spu_index == spu_index else s
            for s in samples
        ]
