# coding: utf-8

from howl_editor.ctr.adventure_hub import HUB_NAMES, TRACK_MASK_BYTES


class AdventureHubMaskTableQuery:
    """Query the per-track hub bitmask used by Adventure Hub layered music."""

    def __init__(
        self,
        mask_bytes: tuple[int, ...] = TRACK_MASK_BYTES,
        hub_names: tuple[str, ...] = HUB_NAMES,
    ):
        self._mask = mask_bytes
        self._hubs = hub_names

    @property
    def num_tracks(self) -> int:
        return len(self._mask)

    @property
    def num_hubs(self) -> int:
        return len(self._hubs)

    def hub_name(self, hub_index: int) -> str:
        return self._hubs[hub_index]

    def hub_names(self) -> tuple[str, ...]:
        return self._hubs

    def tracks_for_hub(self, hub_index: int) -> list[int]:
        """Indices of TRACKS (within the main-music sub-song) that are audible
        in the given hub."""
        bit = 1 << hub_index
        return [i for i, mask in enumerate(self._mask) if mask & bit]

    def track_is_active_in_hub(self, track_index: int, hub_index: int) -> bool:
        if track_index >= len(self._mask):
            return False

        return bool(self._mask[track_index] & (1 << hub_index))

    def hubs_for_track(self, track_index: int) -> list[int]:
        if track_index >= len(self._mask):
            return []

        mask = self._mask[track_index]
        return [i for i in range(len(self._hubs)) if mask & (1 << i)]
