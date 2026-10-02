# coding: utf-8

"""Imported only by the lazy-registration test, so its presence in sys.modules
proves whether the container imported it.
"""


class Probe:
    def __init__(self, *parts):
        self.parts = parts
