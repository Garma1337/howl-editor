# coding: utf-8

# Song-side ranges. Half-open Python `range` objects.
RACE_TRACK_SONG_RANGE = range(0, 18)        # paired with banks 1-18
BATTLE_ARENA_SONG_RANGE = range(18, 25)     # paired with banks 19-25
MENU_SONG_RANGE = range(27, 33)             # paired with banks 32-37

# Shared boss theme — one song fans out across the five boss banks below.
BOSS_SONG_INDEX = 25
BOSS_BANK_RANGE = range(26, 31)

# Per-character "podium" animation banks. Each is at character_bank - 17,
# so Crash Bandicoot (bank 55) → podium bank 38, Oxide (70) → 53.
PODIUM_BANK_RANGE = range(38, 54)
PODIUM_BANK_OFFSET = 17

# Per-character race banks (16 characters + the 8-driver shared bank 54).
CHARACTER_BANK_RANGE = range(54, 71)

# Bank 54 holds the samples of all 8 original drivers. A full 8-driver race
# loads it once instead of eight individual character banks. Only race tracks
# load it — arenas, menus, boss races and the special levels do not.
EIGHT_DRIVER_SHARED_BANK = 54

# Race-track FX banks (paired with race songs 0-17). The only level banks that
# co-load the 8-driver shared bank in a full arcade grid.
RACE_TRACK_BANK_RANGE = range(1, 19)

# The Intro Race and Naughty Dog Crate levels destroy every bank (including the
# universal SFX bank 0) and load only their own dedicated bank, so these banks
# are resident entirely on their own.
NAUGHTY_DOG_CRATE_BANK = 33
INTRO_RACE_BANK = 34
SOLE_RESIDENT_BANKS = (NAUGHTY_DOG_CRATE_BANK, INTRO_RACE_BANK)

# Universal SFX bank — referenced by every song's runtime.
SFX_UNIVERSAL_BANK = 0

# Slots above these thresholds are user-added (no stock meaning).
FIRST_CUSTOM_SONG = 33
FIRST_CUSTOM_BANK = 71

# Song↔bank pairings: a paired bank index is `song_index + offset`. Used
# by the layout handler to look up the bank that goes with a given song.
RACE_TRACK_BANK_OFFSET = 1
BATTLE_ARENA_BANK_OFFSET = 1
MENU_BANK_OFFSET = 5
