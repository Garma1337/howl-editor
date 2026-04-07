# coding: utf-8

from howl_editor.models import HowlFile


class HowlEditor:
    """Provides mutation operations on a HowlFile."""

    def add_bank(self, hwl: HowlFile, bank_data: bytes) -> int:
        """Add a bank blob, returns its new index."""
        hwl.banks.append(bank_data)
        return len(hwl.banks) - 1

    def remove_bank(self, hwl: HowlFile, index: int) -> None:
        """Remove a bank by index. Raises IndexError if out of range."""
        self._validate_index(index, len(hwl.banks), "Bank")
        del hwl.banks[index]

    def replace_bank(self, hwl: HowlFile, index: int, bank_data: bytes) -> None:
        """Replace a bank at index. Raises IndexError if out of range."""
        self._validate_index(index, len(hwl.banks), "Bank")
        hwl.banks[index] = bank_data

    def add_song(self, hwl: HowlFile, song_data: bytes) -> int:
        """Add a song (CSEQ) blob, returns its new index."""
        hwl.songs.append(song_data)
        return len(hwl.songs) - 1

    def remove_song(self, hwl: HowlFile, index: int) -> None:
        """Remove a song by index. Raises IndexError if out of range."""
        self._validate_index(index, len(hwl.songs), "Song")
        del hwl.songs[index]

    def replace_song(self, hwl: HowlFile, index: int, song_data: bytes) -> None:
        """Replace a song at index. Raises IndexError if out of range."""
        self._validate_index(index, len(hwl.songs), "Song")
        hwl.songs[index] = song_data

    def move_bank(self, hwl: HowlFile, from_index: int, to_index: int) -> None:
        """Move a bank from one position to another."""
        self._validate_index(from_index, len(hwl.banks), "Bank")
        self._validate_index(to_index, len(hwl.banks), "Bank")

        bank = hwl.banks.pop(from_index)
        hwl.banks.insert(to_index, bank)

    def move_song(self, hwl: HowlFile, from_index: int, to_index: int) -> None:
        """Move a song from one position to another."""
        self._validate_index(from_index, len(hwl.songs), "Song")
        self._validate_index(to_index, len(hwl.songs), "Song")

        song = hwl.songs.pop(from_index)
        hwl.songs.insert(to_index, song)

    def _validate_index(self, index: int, length: int, label: str) -> None:
        if index < 0 or index >= length:
            raise IndexError(f"{label} index {index} out of range (0..{length - 1})")
