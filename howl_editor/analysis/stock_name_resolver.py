# coding: utf-8

_BANK_NAMES: dict[int, str] = {
    0: "SFX (universal)",
    1: "Dingo Canyon",
    2: "Dragon Mines",
    3: "Blizzard Bluff",
    4: "Crash Cove",
    5: "Tiger Temple",
    6: "Papu's Pyramid",
    7: "Roo's Tubes",
    8: "Hot Air Skyway",
    9: "Sewer Speedway",
    10: "Mystery Caves",
    11: "Cortex Castle",
    12: "N. Gin Labs",
    13: "Polar Pass",
    14: "Oxide Station",
    15: "Coco Park",
    16: "Tiny Arena",
    17: "Slide Coliseum",
    18: "Turbo Track",
    19: "Nitro Court",
    20: "Rampage Ruins",
    21: "Parking Lot",
    22: "Skull Rock",
    23: "The North Bowl",
    24: "Rocky Road",
    25: "Lab Basement",
    26: "Boss: Ripper Roo",
    27: "Boss: Papu Papu",
    28: "Boss: Komodo Joe",
    29: "Boss: Pinstripe",
    30: "Boss: N. Oxide",
    31: "Adventure Hub",
    32: "Main Menu",
    33: "Naughty Dog Crate",
    34: "Intro Race",
    35: "Oxide Ending (Any%)",
    36: "Oxide Ending (100%)",
    37: "Credits",
    38: "Crash Bandicoot (Podium)",
    39: "Dr. Neo Cortex (Podium)",
    40: "Tiny Tiger (Podium)",
    41: "Coco Bandicoot (Podium)",
    42: "N. Gin (Podium)",
    43: "Dingodile (Podium)",
    44: "Polar (Podium)",
    45: "Pura (Podium)",
    46: "Pinstripe (Podium)",
    47: "Papu Papu (Podium)",
    48: "Ripper Roo (Podium)",
    49: "Komodo Joe (Podium)",
    50: "N. Tropy (Podium)",
    51: "Penta Penguin (Podium)",
    52: "Fake Crash (Podium)",
    53: "Oxide (Podium)",
    54: "8-Driver Shared",
    55: "Crash Bandicoot",
    56: "Dr. Neo Cortex",
    57: "Tiny Tiger",
    58: "Coco Bandicoot",
    59: "N. Gin",
    60: "Dingodile",
    61: "Polar",
    62: "Pura",
    63: "Pinstripe",
    64: "Papu Papu",
    65: "Ripper Roo",
    66: "Komodo Joe",
    67: "N. Tropy",
    68: "Penta Penguin",
    69: "Fake Crash",
    70: "Oxide",
}

_SONG_NAMES: dict[int, str] = {
    0: _BANK_NAMES[1],
    1: _BANK_NAMES[2],
    2: _BANK_NAMES[3],
    3: _BANK_NAMES[4],
    4: _BANK_NAMES[5],
    5: _BANK_NAMES[6],
    6: _BANK_NAMES[7],
    7: _BANK_NAMES[8],
    8: _BANK_NAMES[9],
    9: _BANK_NAMES[10],
    10: _BANK_NAMES[11],
    11: _BANK_NAMES[12],
    12: _BANK_NAMES[13],
    13: _BANK_NAMES[14],
    14: _BANK_NAMES[15],
    15: _BANK_NAMES[16],
    16: _BANK_NAMES[17],
    17: _BANK_NAMES[18],
    18: _BANK_NAMES[19],
    19: _BANK_NAMES[20],
    20: _BANK_NAMES[21],
    21: _BANK_NAMES[22],
    22: _BANK_NAMES[23],
    23: _BANK_NAMES[24],
    24: _BANK_NAMES[25],
    25: "Boss Race",
    26: _BANK_NAMES[31],
    27: _BANK_NAMES[32],
    28: _BANK_NAMES[33],
    29: _BANK_NAMES[34],
    30: _BANK_NAMES[35],
    31: _BANK_NAMES[36],
    32: _BANK_NAMES[37],
}


_FIRST_CUSTOM_BANK = 71
_FIRST_CUSTOM_SONG = 33
_CUSTOM_LABEL = "Custom"


class StockNameResolver:
    FIRST_CUSTOM_BANK = _FIRST_CUSTOM_BANK
    FIRST_CUSTOM_SONG = _FIRST_CUSTOM_SONG
    CUSTOM_LABEL = _CUSTOM_LABEL

    def bank_name(self, index: int) -> str:
        if index >= _FIRST_CUSTOM_BANK:
            return _CUSTOM_LABEL

        return _BANK_NAMES.get(index, "")

    def song_name(self, index: int) -> str:
        if index >= _FIRST_CUSTOM_SONG:
            return _CUSTOM_LABEL

        return _SONG_NAMES.get(index, "")
