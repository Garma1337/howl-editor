# coding: utf-8

from dataclasses import dataclass


class ScaFormat:
    """Wire-format constants for the .sca container.

    Layout: [magic(3) | version(1)] then a sequence of chunks where each chunk is
    [tag(4) | bodySize(4 LE) | body(bodySize) | zero-pad to CHUNK_ALIGNMENT].
    """

    MAGIC = b"SCA"
    VERSION = 1
    FILE_HEADER_SIZE = 4  # 3-byte magic + 1-byte version

    CHUNK_TAG_SIZE = 4
    CHUNK_BODY_SIZE_FIELD = 4
    CHUNK_HEADER_SIZE = CHUNK_TAG_SIZE + CHUNK_BODY_SIZE_FIELD
    CHUNK_ALIGNMENT = 4

    TAG_BANK = b"BANK"
    TAG_CSEQ = b"CSEQ"
    TAG_SIZE = b"SIZE"
    TAG_META = b"META"

    META_ENCODING = "utf-8"
    META_KEY_NAME = "name"
    META_KEY_AUTHOR = "author"


@dataclass
class ScaMetadata:
    name: str
    author: str


@dataclass
class ScaFile:
    bank: bytes
    cseq: bytes
    sample_sizes: list[int]   # u16 spuSize values in 8-byte units, in bank-header order
    metadata: ScaMetadata
