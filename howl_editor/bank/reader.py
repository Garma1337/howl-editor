# coding: utf-8

from struct import unpack_from

from howl_editor.constants import SECTOR_SIZE, bytes_to_sectors
from howl_editor.models import SpuAddrEntry, BankSample

# Missing indices are banks without names
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
    31: "Battle Arenas", 
    32: "Main Menu",
    33: "Naughty Dog Crate", 
    34: "Intro Race",
    35: "Oxide Ending (Any%)", 
    36: "Oxide Ending (100%)", 
    37: "Credits",
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

_FIRST_CUSTOM_BANK = 71


class BankReader:

    def get_name(self, index: int) -> str:
        if index >= _FIRST_CUSTOM_BANK:
            return "Custom"

        return _BANK_NAMES.get(index, "")

    def parse(self, bank_data: bytes, spu_addrs: list[SpuAddrEntry]) -> list[BankSample]:
        """
        Parse a bank blob into individual samples.
        Requires the global SPU address table for sample sizes.
        """
        num_samples = self._read_sample_count(bank_data)
        if num_samples == 0:
            return []

        sample_ids = self._read_sample_ids(bank_data, num_samples)
        data_offset = self._calculate_data_offset(num_samples)
        
        return self._extract_samples(bank_data, sample_ids, spu_addrs, data_offset)

    def _read_sample_count(self, data: bytes) -> int:
        if len(data) < 2:
            return 0
        
        count = unpack_from("<H", data, 0)[0]
        return count if count < 1024 else 0

    def _read_sample_ids(self, data: bytes, count: int) -> list[int]:
        ids = []
        for i in range(count):
            offset = 2 + i * 2

            if offset + 2 > len(data):
                break

            sid = unpack_from("<h", data, offset)[0]
            ids.append(sid)

        return ids

    def _calculate_data_offset(self, num_samples: int) -> int:
        header_bytes = 2 + num_samples * 2
        return bytes_to_sectors(header_bytes) * SECTOR_SIZE

    def _extract_samples(
        self,
        data: bytes,
        sample_ids: list[int],
        spu_addrs: list[SpuAddrEntry],
        data_offset: int,
    ) -> list[BankSample]:
        samples = []
        pos = data_offset
        for sid in sample_ids:
            if sid < 0 or sid >= len(spu_addrs):
                continue

            size = spu_addrs[sid].byte_size
            if pos + size <= len(data):
                samples.append(BankSample(spu_index=sid, data=data[pos:pos + size]))
            
            pos += size
        
        return samples
