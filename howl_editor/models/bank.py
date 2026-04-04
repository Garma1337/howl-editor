# coding: utf-8

from dataclasses import dataclass, field


@dataclass
class BankSample:
    """A single sample extracted from a bank blob."""
    spu_index: int
    data: bytes


@dataclass
class BankBuildResult:
    """Result of building a bank from VAG files."""
    bank_data: bytes
    new_spu_indices: list[int] = field(default_factory=list)
