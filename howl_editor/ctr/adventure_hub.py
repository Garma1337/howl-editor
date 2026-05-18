# coding: utf-8

# HOWL slot positions for the layered hub theme + its shared bank.
SONG_INDEX = 26
BANK_INDEX = 31

# The main-music sub-song has this many tracks layered. Replacements need
# to preserve the count or the per-hub mask stops indexing correctly.
NUM_TRACKS = 20

# Five hub worlds, in bit order. Bit 0 = Gem Stone Valley, bit 4 = Citadel City.
HUB_NAMES: tuple[str, ...] = (
    "Gem Stone Valley",
    "N. Sanity Beach",
    "The Lost Ruins",
    "Glacier Park",
    "Citadel City",
)

# One byte per track of the main-music sub-song (20 tracks). The low 5 bits
# select hubs: bit N => HUB_NAMES[N]. A track is audible in a given hub iff
# its mask byte has the hub's bit set.
TRACK_MASK_BYTES: tuple[int, ...] = (
    0x1F, 0x17, 0x08, 0x1F, 0x10, 0x1F, 0x01, 0x08,
    0x01, 0x10, 0x01, 0x1F, 0x04, 0x04, 0x02, 0x1F,
    0x10, 0x08, 0x10, 0x02,
)
