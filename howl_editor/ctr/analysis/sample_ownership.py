# coding: utf-8

from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile


class SampleOwnershipResolver:
    """Answers which banks claim a given SPU sample id.

    The SPU id space is global and heavily shared — a universal effect can be
    claimed by thirty banks at once — while each claiming bank carries its own
    copy of the bytes. Anything that edits a sample therefore has to know who
    else is holding it."""

    def __init__(self, bank_reader: BankReader):
        self._bank_reader = bank_reader

    def owners(self, hwl: HowlFile, spu_index: int) -> list[int]:
        """Bank indices whose header declares `spu_index`, in bank order."""
        return [
            bank_index
            for bank_index, blob in enumerate(hwl.banks)
            if spu_index in self._ids(blob)
        ]

    def other_owners(self, hwl: HowlFile, spu_index: int, bank_index: int) -> list[int]:
        """Owners excluding the bank being edited — the banks that would be
        left holding stale bytes if this sample's size changed."""
        return [b for b in self.owners(hwl, spu_index) if b != bank_index]

    def _ids(self, blob: bytes) -> list[int]:
        try:
            return self._bank_reader.sample_ids(blob)
        except Exception:
            return []
