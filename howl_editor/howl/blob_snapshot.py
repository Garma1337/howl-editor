# coding: utf-8

from howl_editor.models import HowlFile


class BlobSnapshot:
    """Holds a snapshot of bank and song blobs from the moment a HWL file was
    loaded, so the Main tab can detect modifications and offer "Reset to stock"."""

    def __init__(self):
        self._banks: list[bytes] | None = None
        self._songs: list[bytes] | None = None

    @property
    def banks(self) -> list[bytes] | None:
        return self._banks

    @property
    def songs(self) -> list[bytes] | None:
        return self._songs

    def capture(self, hwl: HowlFile) -> None:
        """Snapshot the current banks and songs as the new originals."""
        self._banks = list(hwl.banks)
        self._songs = list(hwl.songs)

    def clear(self) -> None:
        self._banks = None
        self._songs = None

    def has_snapshot(self) -> bool:
        return self._banks is not None

    def original_bank(self, index: int) -> bytes | None:
        if self._banks is None or index < 0 or index >= len(self._banks):
            return None

        return self._banks[index]

    def original_song(self, index: int) -> bytes | None:
        if self._songs is None or index < 0 or index >= len(self._songs):
            return None

        return self._songs[index]
