# coding: utf-8

class TrackMaskLayout:
    """The mask-sequence naming convention for CTR songs 0-27.

    Used by the Main tab's expanded panel for race-track, battle-arena, boss,
    adventure-hub and character-select rows so users can play and replace each
    of the 3 mask slots individually.
    """

    LAST_SONG_WITH_MASKS = 27
    NUM_MASK_SLOTS = 3
    MAIN_SEQUENCE = 0
    AKU_SEQUENCE = 1
    UKA_SEQUENCE = 2

    _NAMES = (
        "Main music",
        "Aku Aku mask",
        "Uka Uka mask",
    )

    _ICONS = (
        "🎵",
        "🪄",
        "👹",
    )

    def applies_to(self, song_index: int) -> bool:
        return 0 <= song_index <= self.LAST_SONG_WITH_MASKS

    def name_for(self, seq_index: int) -> str:
        if 0 <= seq_index < len(self._NAMES):
            return self._NAMES[seq_index]

        return f"Sequence {seq_index}"

    def icon_for(self, seq_index: int) -> str:
        if 0 <= seq_index < len(self._ICONS):
            return self._ICONS[seq_index]

        return "•"

    def mask_slots(self) -> tuple[int, ...]:
        return tuple(range(self.NUM_MASK_SLOTS))
