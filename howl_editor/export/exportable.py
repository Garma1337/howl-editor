# coding: utf-8

from dataclasses import dataclass
from enum import Enum


class ExportableKind(Enum):
    BANK = "bank"
    SAMPLE = "sample"
    SONG = "song"
    SEQUENCE = "sequence"


@dataclass(frozen=True)
class ExportableContext:
    """Indices needed to locate the actual content inside a HowlFile.

    Each kind reads only the fields it needs (sample needs bank+sample;
    sequence needs song+seq; bank/song each need their own slot index).
    """
    song_index: int | None = None
    seq_index: int | None = None
    bank_index: int | None = None
    sample_index: int | None = None
