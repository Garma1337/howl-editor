# coding: utf-8

from howl_editor.ctr import stock_layout as data


class StockLayoutResolver:
    """Stock NTSC-U HOWL layout: index ranges per category and song↔bank pairing."""

    def __init__(self):
        self._song_to_bank: dict[int, int] = {}

        for s in data.RACE_TRACK_SONG_RANGE:
            self._song_to_bank[s] = s + data.RACE_TRACK_BANK_OFFSET

        for s in data.BATTLE_ARENA_SONG_RANGE:
            self._song_to_bank[s] = s + data.BATTLE_ARENA_BANK_OFFSET

        for s in data.MENU_SONG_RANGE:
            self._song_to_bank[s] = s + data.MENU_BANK_OFFSET

    def paired_bank(self, song_index: int) -> int | None:
        return self._song_to_bank.get(song_index)

    def is_race_track_song(self, song_index: int) -> bool:
        return song_index in data.RACE_TRACK_SONG_RANGE

    def is_battle_arena_song(self, song_index: int) -> bool:
        return song_index in data.BATTLE_ARENA_SONG_RANGE

    def is_menu_song(self, song_index: int) -> bool:
        return song_index in data.MENU_SONG_RANGE

    def is_character_bank(self, bank_index: int) -> bool:
        return bank_index in data.CHARACTER_BANK_RANGE

    def is_podium_bank(self, bank_index: int) -> bool:
        return bank_index in data.PODIUM_BANK_RANGE

    def podium_bank_for_character(self, character_bank_index: int) -> int | None:
        candidate = character_bank_index - data.PODIUM_BANK_OFFSET

        if candidate in data.PODIUM_BANK_RANGE:
            return candidate

        return None

    def is_boss_bank(self, bank_index: int) -> bool:
        return bank_index in data.BOSS_BANK_RANGE

    def is_custom_song(self, song_index: int) -> bool:
        return song_index >= data.FIRST_CUSTOM_SONG

    def is_custom_bank(self, bank_index: int) -> bool:
        return bank_index >= data.FIRST_CUSTOM_BANK
