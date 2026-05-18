# coding: utf-8

class StockLayout:
    """Stock NTSC-U HOWL layout: index ranges per category and song↔bank pairing."""

    RACE_TRACK_SONG_RANGE = range(0, 18)        # banks 1-18
    BATTLE_ARENA_SONG_RANGE = range(18, 25)     # banks 19-25
    BOSS_SONG_INDEX = 25                        # shared song; banks 26-30
    BOSS_BANK_RANGE = range(26, 31)
    MENU_SONG_RANGE = range(27, 33)             # banks 32-37
    PODIUM_BANK_RANGE = range(38, 54)
    PODIUM_BANK_OFFSET = 17
    CHARACTER_BANK_RANGE = range(54, 71)
    SFX_UNIVERSAL_BANK = 0
    FIRST_CUSTOM_SONG = 33
    FIRST_CUSTOM_BANK = 71

    def __init__(self):
        self._song_to_bank: dict[int, int] = {}
        for s in self.RACE_TRACK_SONG_RANGE:
            self._song_to_bank[s] = s + 1

        for s in self.BATTLE_ARENA_SONG_RANGE:
            self._song_to_bank[s] = s + 1

        for s in self.MENU_SONG_RANGE:
            self._song_to_bank[s] = s + 5

    def paired_bank(self, song_index: int) -> int | None:
        return self._song_to_bank.get(song_index)

    def is_race_track_song(self, song_index: int) -> bool:
        return song_index in self.RACE_TRACK_SONG_RANGE

    def is_battle_arena_song(self, song_index: int) -> bool:
        return song_index in self.BATTLE_ARENA_SONG_RANGE

    def is_menu_song(self, song_index: int) -> bool:
        return song_index in self.MENU_SONG_RANGE

    def is_character_bank(self, bank_index: int) -> bool:
        return bank_index in self.CHARACTER_BANK_RANGE

    def is_podium_bank(self, bank_index: int) -> bool:
        return bank_index in self.PODIUM_BANK_RANGE

    def podium_bank_for_character(self, character_bank_index: int) -> int | None:
        candidate = character_bank_index - self.PODIUM_BANK_OFFSET

        if candidate in self.PODIUM_BANK_RANGE:
            return candidate

        return None

    def is_boss_bank(self, bank_index: int) -> bool:
        return bank_index in self.BOSS_BANK_RANGE

    def is_custom_song(self, song_index: int) -> bool:
        return song_index >= self.FIRST_CUSTOM_SONG

    def is_custom_bank(self, bank_index: int) -> bool:
        return bank_index >= self.FIRST_CUSTOM_BANK
