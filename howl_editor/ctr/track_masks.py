# coding: utf-8

"""Per-track mask convention used by CTR songs 0-27.

Each affected song's CSEQ contains three sub-songs:

    sub-song 0 — Main music
    sub-song 1 — Aku Aku mask music
    sub-song 2 — Uka Uka mask music
"""

LAST_SONG_WITH_MASKS = 27
NUM_MASK_SLOTS = 3

MAIN_SEQUENCE = 0
AKU_SEQUENCE = 1
UKA_SEQUENCE = 2

# Display names + leaf icons keyed by sub-song index.
SLOT_NAMES: tuple[str, ...] = (
    "Main music",
    "Aku Aku mask",
    "Uka Uka mask",
)

SLOT_ICONS: tuple[str, ...] = (
    "🎵",
    "🪄",
    "👹",
)

# Fallback used when a sub-song index falls outside the mask layout.
GENERIC_SEQUENCE_ICON = "🎵"
