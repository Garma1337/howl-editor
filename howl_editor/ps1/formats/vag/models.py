# coding: utf-8

from dataclasses import dataclass
from struct import Struct


@dataclass
class VagSample:
    MAGIC = b"VAGp"
    HEADER_SIZE = 48
    HEADER_STRUCT = Struct(">4sIIII")  # magic, version, reserved, data_size, sample_rate

    sample_rate: int = 44100
    name: str = ""
    data: bytes = b""
