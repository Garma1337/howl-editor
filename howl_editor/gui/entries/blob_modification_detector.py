# coding: utf-8


class BlobModificationDetector:
    """Compares a current list of blobs to a snapshot, returning which indices
    have been modified or added since the snapshot was taken."""

    def modified_indices(
        self,
        current: list[bytes],
        original: list[bytes] | None,
    ) -> set[int]:
        if original is None:
            return set()

        return {
            i for i, blob in enumerate(current)
            if i >= len(original) or blob != original[i]
        }

    def is_modified(
        self,
        current: list[bytes],
        original: list[bytes] | None,
        index: int,
    ) -> bool:
        if original is None or index < 0 or index >= len(current):
            return False

        if index >= len(original):
            return True

        return current[index] != original[index]
