# coding: utf-8

from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotGuard
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.reader import CseqReader


class ScaSpuSlotValidator:
    """Finds the SPU slots in an export that Saphi cannot load.

    Saphi resolves both the bank's sample ids and the song's descriptors
    against the player's vanilla table, so both are checked here."""

    def __init__(self, bank_reader: BankReader, cseq_reader: CseqReader, slot_guard: SpuSlotGuard):
        self._bank_reader = bank_reader
        self._cseq_reader = cseq_reader
        self._slot_guard = slot_guard

    def out_of_range_slots(self, bank_blob: bytes, cseq_blob: bytes) -> list[int]:
        """The distinct slots, sorted, that the bank or song uses past the stock table."""
        cseq = self._cseq_reader.read(cseq_blob)
        referenced = [x.sample_id for x in cseq.instruments] + [x.sample_id for x in cseq.percussions]

        return self._slot_guard.out_of_range(self._bank_reader.sample_ids(bank_blob) + referenced)
