# coding: utf-8

from dataclasses import dataclass

from howl_editor.ctr.formats.howl.collections import HowlCollection


@dataclass(frozen=True)
class HowlChange:
    """What an edit touched, so the views can update that instead of
    rebuilding themselves.

    `structural` says every later index moved - an item was added, removed or
    reordered - so lists have to be rebuilt rather than repainted. A
    `collection` of None means the change is not confined to one blob.
    """

    collection: HowlCollection | None = None
    index: int | None = None
    sub_index: int | None = None
    structural: bool = False

    @property
    def is_file_wide(self) -> bool:
        return self.collection is None or self.index is None

    def touches(self, collection: HowlCollection, index: int) -> bool:
        """Whether a view showing `collection[index]` has to update."""
        if self.is_file_wide or self.structural:
            return True

        return self.collection == collection and self.index == index

    def merged_with(self, other: "HowlChange") -> "HowlChange":
        """One descriptor covering both, for edits that arrive as a burst.

        Two changes to the same blob stay precise; anything else widens to
        file-wide, which is correct if blunt.
        """
        structural = self.structural or other.structural

        if self.collection == other.collection and self.index == other.index:
            return HowlChange(
                collection=self.collection,
                index=self.index,
                sub_index=self.sub_index if self.sub_index == other.sub_index else None,
                structural=structural,
            )

        return HowlChange(structural=structural)
