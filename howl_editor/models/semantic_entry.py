# coding: utf-8

from dataclasses import dataclass, field
from enum import Enum


class EntryKind(Enum):
    TRACK = "track"            # paired song + bank (race tracks, battle arenas, menus)
    SHARED_SONG = "shared"     # song with no per-entry bank (Boss Race shared theme)
    BANK_ONLY = "bank_only"    # bank with no paired song (characters, SFX universal)
    ADVENTURE_HUB = "hub"      # song 26 + bank 31, layered, special view
    OTHER_FX = "other_fx"      # single OtherFX entry
    ENGINE_FX = "engine_fx"    # single EngineFX entry
    CUSTOM_SONG = "custom_song"
    CUSTOM_BANK = "custom_bank"


@dataclass
class EntryRow:
    kind: EntryKind
    name: str
    song_index: int | None = None
    bank_index: int | None = None
    fx_index: int | None = None     # for OTHER_FX / ENGINE_FX
    is_modified: bool = False       # vs. original loaded blob
    is_broken: bool = False         # validation: song refs samples bank lacks
    missing_count: int = 0
    accepts: tuple[str, ...] = ()   # accepted drop extensions, e.g. (".mid", ".cseq", ".sca")


@dataclass
class EntryGroup:
    name: str
    icon: str                       # short text/emoji prefix
    rows: list[EntryRow] = field(default_factory=list)
    collapsed_by_default: bool = False
