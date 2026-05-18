# coding: utf-8

"""PS1 platform constants."""


# The PlayStation CD-ROM uses 2048-byte (Mode 2 Form 1) sectors. PS1 game
# data is always aligned to this boundary so the loader can DMA whole
# sectors directly off the disc.
SECTOR_SIZE = 0x800


def bytes_to_sectors(n: int) -> int:
    """Round up a byte count to the number of disc sectors that hold it."""
    return (n + SECTOR_SIZE - 1) // SECTOR_SIZE
