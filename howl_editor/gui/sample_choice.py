# coding: utf-8

from dataclasses import dataclass


@dataclass(frozen=True)
class SampleChoice:
    """One row in the sample/slot picker. `display` is the user-visible label,
    `spu_index` is what the caller wires back. `free` marks a slot nothing
    references; `enabled` False shows a row that cannot be picked."""
    spu_index: int
    display: str
    free: bool = False
    enabled: bool = True
    tooltip: str = ""
