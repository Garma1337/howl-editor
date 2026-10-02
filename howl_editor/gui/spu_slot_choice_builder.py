# coding: utf-8

from howl_editor.ctr import constants
from howl_editor.ctr.analysis.spu_slot_allocator import SpuSlotAllocator
from howl_editor.ctr.analysis.spu_slot_usage import SpuSlotUsageResolver
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.gui.sample_choice import SampleChoice


class SpuSlotChoiceBuilder:
    """Builds the rows of the two SPU slot pickers, marking the free slots."""

    FREE_TARGET_TIP = (
        "Free slot — no bank holds a sample here, so an instrument pointing at it plays silence."
    )
    FREE_NEW_TIP = "Free slot — nothing uses it, so the new sample can take it."
    USED_TIP = "In use — a bank, sound effect or song already references this slot."
    PAST_STOCK_TIP = (
        f"Past the stock {constants.MAX_SPU_SLOTS}-slot table — new samples cannot go here."
    )

    def __init__(
        self, bank_reader: BankReader, usage: SpuSlotUsageResolver, allocator: SpuSlotAllocator,
    ):
        self._bank_reader = bank_reader
        self._usage = usage
        self._allocator = allocator

    def sample_targets(self, hwl: HowlFile) -> list[SampleChoice]:
        """Every slot, pickable, for pointing an instrument or percussion at."""
        free = self._usage.free_slots(hwl)
        owners = self._first_owners(hwl)

        return [
            SampleChoice(
                spu_index=i,
                display=self._slot_label(hwl, i, owners),
                free=i in free,
                tooltip=self.FREE_TARGET_TIP if i in free else "",
            )
            for i in range(len(hwl.spu_addrs))
        ]

    def new_sample_slots(self, hwl: HowlFile, share_spu: int | None = None) -> list[SampleChoice]:
        """Where a new sample can go: free slots, a fresh slot while the table
        has room, and `share_spu` to reuse a copied sample's own slot."""
        free = self._usage.free_slots(hwl)
        owners = self._first_owners(hwl)
        out: list[SampleChoice] = []

        if share_spu is not None:
            out.append(SampleChoice(
                spu_index=share_spu,
                display=f"SPU #{share_spu:>4} · share the source sample's slot (uses no slot)",
                tooltip="Both banks point at the same slot, like the stock game's shared samples.",
            ))

        if len(hwl.spu_addrs) < constants.MAX_SPU_SLOTS:
            new_index = len(hwl.spu_addrs)
            out.append(SampleChoice(
                spu_index=new_index,
                display=f"SPU #{new_index:>4} · new slot at the end of the table",
            ))

        for i in range(len(hwl.spu_addrs)):
            out.append(SampleChoice(
                spu_index=i,
                display=self._slot_label(hwl, i, owners),
                free=i in free,
                enabled=i in free,
                tooltip=self._new_slot_tip(i, free),
            ))

        return out

    def default_new_slot(self, hwl: HowlFile, share_spu: int | None = None) -> int | None:
        return share_spu if share_spu is not None else self._allocator.default_slot(hwl)

    def _new_slot_tip(self, spu_index: int, free: set[int]) -> str:
        if spu_index in free:
            return self.FREE_NEW_TIP

        if spu_index >= constants.MAX_SPU_SLOTS:
            return self.PAST_STOCK_TIP

        return self.USED_TIP

    def _slot_label(self, hwl: HowlFile, spu_index: int, owners: dict[int, int]) -> str:
        size = hwl.spu_addrs[spu_index].byte_size
        bank_index = owners.get(spu_index)

        if bank_index is None:
            bank_label = "—"
        else:
            name = self._bank_reader.get_name(bank_index)
            bank_label = f"Bank {bank_index} — {name}" if name else f"Bank {bank_index}"

        return f"SPU #{spu_index:>4} · {size:>6} B · {bank_label}"

    def _first_owners(self, hwl: HowlFile) -> dict[int, int]:
        """First bank declaring each slot — one header pass, not a parse per slot."""
        owners: dict[int, int] = {}

        for bank_index, blob in enumerate(hwl.banks):
            try:
                ids = self._bank_reader.sample_ids(blob)
            except Exception:
                continue

            for spu_index in ids:
                owners.setdefault(spu_index, bank_index)

        return owners
