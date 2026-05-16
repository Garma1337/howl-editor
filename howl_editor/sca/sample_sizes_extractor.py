# coding: utf-8

from howl_editor.bank.reader import BankReader
from howl_editor.models import SpuAddrEntry


class SampleSizesExtractor:
    """Extracts the SCA `SIZE` chunk payload (per-sample SPU sizes) from a bank blob."""

    def __init__(self, bank_reader: BankReader):
        self._bank_reader = bank_reader

    def extract(self, bank_blob: bytes, spu_addrs: list[SpuAddrEntry]) -> list[int]:
        """Return the spuSize value for each sample in the bank, in bank-header order.
        Sizes are in 8-byte SPU units (the same units the SCA SIZE chunk stores)."""
        samples = self._bank_reader.parse(bank_blob, spu_addrs)
        return [spu_addrs[s.spu_index].size for s in samples]
