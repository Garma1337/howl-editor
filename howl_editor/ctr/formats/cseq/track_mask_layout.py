# coding: utf-8

from howl_editor.ctr import track_masks


class TrackMaskLayout:
    """Resolve sub-song indices to their mask-slot name/icon for CTR songs
    in the 0..27 range. Behavior only — see `howl_editor.ctr.track_masks`
    for the source data."""

    def applies_to(self, song_index: int) -> bool:
        return 0 <= song_index <= track_masks.LAST_SONG_WITH_MASKS

    def name_for(self, seq_index: int) -> str:
        if 0 <= seq_index < len(track_masks.SLOT_NAMES):
            return track_masks.SLOT_NAMES[seq_index]

        return f"Sequence {seq_index}"

    def icon_for(self, seq_index: int) -> str:
        if 0 <= seq_index < len(track_masks.SLOT_ICONS):
            return track_masks.SLOT_ICONS[seq_index]

        return "•"

    def mask_slots(self) -> tuple[int, ...]:
        return tuple(range(track_masks.NUM_MASK_SLOTS))
