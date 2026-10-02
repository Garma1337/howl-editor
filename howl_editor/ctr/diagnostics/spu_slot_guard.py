# coding: utf-8

from collections.abc import Iterable

from howl_editor.ctr import constants
from howl_editor.ctr.formats.howl.models import SpuAddrEntry


class SpuSlotLimitError(ValueError):
    """Raised when a mutation would create an SPU slot past the stock table."""


class SpuSlotGuard:
    """Keeps new samples inside the retail SPU address table (slots 0-527).
    Slots past it only exist in a HOWL that ships its own larger table.
    """

    def out_of_range(self, spu_indices: Iterable[int]) -> list[int]:
        """The distinct indices at or past the stock table, sorted."""
        return sorted({i for i in spu_indices if i >= constants.MAX_SPU_SLOTS})

    def ensure_creatable(self, spu_addrs: list[SpuAddrEntry], spu_indices: Iterable[int]) -> None:
        """Raise if any index would add a new slot at or past the stock table.

        Indices that already exist in `spu_addrs` are reuses, not creations,
        so files that already carry such slots stay editable."""
        new = [i for i in spu_indices if i >= len(spu_addrs)]
        blocked = self.out_of_range(new)

        if blocked:
            raise SpuSlotLimitError(
                f"Cannot create SPU slot(s) {', '.join(map(str, blocked))}: new samples must use "
                f"slots 0-{constants.MAX_SPU_SLOTS - 1}. The stock game only has "
                f"{constants.MAX_SPU_SLOTS} slots, and Saphi loads custom music against that "
                f"table, so higher slots overwrite sound effects in memory and play silence. "
                f"Replace an existing sample instead of adding a new one."
            )
