# coding: utf-8

from dataclasses import dataclass

from howl_editor.ps1.constants import SECTOR_SIZE


@dataclass(frozen=True)
class HowlSizeCheck:
    within_limit: bool
    current_bytes: int
    original_bytes: int | None
    current_sectors: int
    original_sectors: int
    over_sectors: int
    warning_text: str


class HowlSizeGuard:
    """Checks whether a saved HOWL still fits the disc slot it was loaded from.

    The file sits at a fixed position in the ISO (its LBA is resolved from the
    filesystem at runtime), occupying a whole number of 0x800-byte sectors.
    Growing it past that sector count shifts every file placed after it on the
    disc. With no on-disc baseline (a brand-new file) there is nothing to
    compare against, so the check passes.
    """

    def check(self, current_bytes: int, original_bytes: int | None) -> HowlSizeCheck:
        if original_bytes is None:
            return HowlSizeCheck(
                within_limit=True,
                current_bytes=current_bytes,
                original_bytes=None,
                current_sectors=self._sectors(current_bytes),
                original_sectors=0,
                over_sectors=0,
                warning_text="",
            )

        current_sectors = self._sectors(current_bytes)
        original_sectors = self._sectors(original_bytes)
        over_sectors = max(0, current_sectors - original_sectors)
        within = over_sectors == 0

        text = "" if within else (
            f"This HOWL is now {current_bytes} bytes and needs {current_sectors} disc "
            f"sectors — {over_sectors} more than the original file "
            f"({original_sectors} sectors). On the disc the file sits at a fixed "
            f"position, so growing it shifts every file after it and can corrupt the "
            f"game's data layout. Rebuild the ISO after saving, or reduce the file's "
            f"size (fewer / smaller banks and songs).\n\nSave it anyway?"
        )

        return HowlSizeCheck(
            within_limit=within,
            current_bytes=current_bytes,
            original_bytes=original_bytes,
            current_sectors=current_sectors,
            original_sectors=original_sectors,
            over_sectors=over_sectors,
            warning_text=text,
        )

    def _sectors(self, byte_count: int) -> int:
        return (byte_count + SECTOR_SIZE - 1) // SECTOR_SIZE
