# coding: utf-8

from dataclasses import dataclass
from enum import Enum


class LeafKind(Enum):
    SEQUENCE = "sequence"   # one playable sequence inside a CSEQ song
    SAMPLE = "sample"       # one playable sample inside a bank


@dataclass
class EntryLeaf:
    """A single playable unit inside an entry — either a sequence of a song or
    a sample of a bank. Each leaf is the unit the user can Play / Replace /
    Export individually on the Main tab."""

    kind: LeafKind
    name: str                       # e.g. "Main music", "Aku Aku mask", "Sample 0"
    icon: str                       # leading emote
    song_index: int | None = None
    seq_index: int | None = None
    bank_index: int | None = None
    sample_index: int | None = None
    spu_index: int | None = None
