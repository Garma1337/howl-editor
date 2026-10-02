# coding: utf-8

from howl_editor.ctr import constants
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.parse_cache import CseqParseCache
from howl_editor.ctr.formats.howl.models import HowlFile


class SpuSlotUsageResolver:
    """Finds the SPU slots nothing uses, so a new sample can take one instead
    of growing the table past MAX_SPU_SLOTS.

    Free means no bank, no OtherFX or EngineFX entry and no song descriptor
    references it — any of those would sound the new sample in its place."""

    def __init__(self, bank_reader: BankReader, cseq_parses: CseqParseCache):
        self._bank_reader = bank_reader
        self._cseq_parses = cseq_parses

    def free_slots(self, hwl: HowlFile) -> set[int]:
        used = self._used(hwl)
        limit = min(len(hwl.spu_addrs), constants.MAX_SPU_SLOTS)

        return {i for i in range(limit) if i not in used}

    def _used(self, hwl: HowlFile) -> set[int]:
        used = {fx.spu_index for fx in hwl.other_fx}
        used |= {fx.spu_index for fx in hwl.engine_fx}

        for blob in hwl.banks:
            used |= set(self._bank_ids(blob))

        for blob in hwl.songs:
            used |= self._song_ids(blob)

        return used

    def _bank_ids(self, blob: bytes) -> list[int]:
        try:
            return self._bank_reader.sample_ids(blob)
        except Exception:
            return []

    def _song_ids(self, blob: bytes) -> set[int]:
        try:
            cseq = self._cseq_parses.read(blob)
        except Exception:
            return set()

        return {x.sample_id for x in cseq.instruments} | {x.sample_id for x in cseq.percussions}
