# coding: utf-8

ADVENTURE_HUB_SONG_INDEX = 26
ADVENTURE_HUB_BANK_INDEX = 31
ADVENTURE_HUB_NUM_SEQUENCES = 20

HUB_NAMES: tuple[str, ...] = (
    "Gem Stone Valley",
    "N. Sanity Beach",
    "The Lost Ruins",
    "Glacier Park",
    "Citadel City",
)

# One byte per sequence; low 5 bits select hubs (bit N => HUB_NAMES[N]).
ADVENTURE_HUB_MASK_BYTES: tuple[int, ...] = (
    0x1F, 0x17, 0x08, 0x1F, 0x10, 0x1F, 0x01, 0x08,
    0x01, 0x10, 0x01, 0x1F, 0x04, 0x04, 0x02, 0x1F,
    0x10, 0x08, 0x10, 0x02,
)


class AdventureHubMaskTable:
    """Query the per-sequence hub bitmask used by Adventure Hub layered music."""

    def __init__(
        self,
        mask_bytes: tuple[int, ...] = ADVENTURE_HUB_MASK_BYTES,
        hub_names: tuple[str, ...] = HUB_NAMES,
    ):
        self._mask = mask_bytes
        self._hubs = hub_names

    @property
    def num_sequences(self) -> int:
        return len(self._mask)

    @property
    def num_hubs(self) -> int:
        return len(self._hubs)

    def hub_name(self, hub_index: int) -> str:
        return self._hubs[hub_index]

    def hub_names(self) -> tuple[str, ...]:
        return self._hubs

    def sequences_for_hub(self, hub_index: int) -> list[int]:
        """Indices of sequences that play in the given hub."""
        bit = 1 << hub_index
        return [i for i, mask in enumerate(self._mask) if mask & bit]

    def hubs_for_sequence(self, seq_index: int) -> list[int]:
        """Indices of hubs that hear the given sequence."""
        if seq_index >= len(self._mask):
            return []

        mask = self._mask[seq_index]
        return [i for i in range(len(self._hubs)) if mask & (1 << i)]

    def sequence_hub_matrix(self) -> list[list[bool]]:
        """Rows = sequences, cols = hubs; True if the sequence plays in that hub."""
        return [
            [bool(mask & (1 << h)) for h in range(len(self._hubs))]
            for mask in self._mask
        ]
