# coding: utf-8

from dataclasses import dataclass


@dataclass
class VagSample:
    sample_rate: int = 44100
    name: str = ""
    data: bytes = b""
