# coding: utf-8

from importlib.util import find_spec

HAS_MIDO = find_spec("mido") is not None
