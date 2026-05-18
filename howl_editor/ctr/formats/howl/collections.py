# coding: utf-8

"""Enum of HowlFile's bulk-data collections."""

from enum import Enum


class HowlCollection(str, Enum):
    BANKS = "banks"
    SONGS = "songs"
