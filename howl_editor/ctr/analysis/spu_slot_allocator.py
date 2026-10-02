# coding: utf-8

from howl_editor.ctr import constants
from howl_editor.ctr.analysis.spu_slot_usage import SpuSlotUsageResolver
from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotLimitError
from howl_editor.ctr.formats.howl.models import HowlFile


class SpuSlotAllocator:
    """Picks the SPU slots new samples go into: appends while the table is
    below MAX_SPU_SLOTS, then falls back to the lowest free slots."""

    def __init__(self, usage: SpuSlotUsageResolver):
        self._usage = usage

    def default_slot(self, hwl: HowlFile) -> int | None:
        """The slot a single new sample would get, or None if none is left."""
        candidates = self._candidates(hwl)
        return candidates[0] if candidates else None

    def allocate(self, hwl: HowlFile, count: int) -> list[int]:
        """Slots for `count` new samples. Raises if not enough are available."""
        candidates = self._candidates(hwl)

        if len(candidates) < count:
            raise SpuSlotLimitError(
                f"Not enough SPU slots for {count} new sample(s): only {len(candidates)} "
                f"left of the stock {constants.MAX_SPU_SLOTS}. Remove unused samples from "
                f"every bank that holds them to free their slots, or replace existing "
                f"samples instead."
            )

        return candidates[:count]

    def _candidates(self, hwl: HowlFile) -> list[int]:
        appended = list(range(len(hwl.spu_addrs), constants.MAX_SPU_SLOTS))
        return appended + sorted(self._usage.free_slots(hwl))
