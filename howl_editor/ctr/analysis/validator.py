# coding: utf-8

from dataclasses import dataclass, field

from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.models import CseqFile
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import SpuAddrEntry


@dataclass
class ValidationResult:
    valid: bool
    missing_ids: list[int] = field(default_factory=list)
    present_ids: list[int] = field(default_factory=list)

    @property
    def message(self) -> str:
        total = len(self.present_ids) + len(self.missing_ids)

        if self.valid:
            return f"Valid: all {total} required samples are present."

        lines = [
            f"{len(self.present_ids)} of {total} required samples present.",
            f"{len(self.missing_ids)} missing:",
            "",
        ]

        for sid in self.missing_ids:
            lines.append(f"  SPU {sid}")

        return "\n".join(lines)


class BankCseqValidator:

    def __init__(self, bank_reader: BankReader, cseq_reader: CseqReader):
        self._bank_reader = bank_reader
        self._cseq_reader = cseq_reader

    def validate(
        self,
        bank_data: bytes,
        song_data: bytes,
        spu_addrs: list[SpuAddrEntry],
    ) -> ValidationResult:
        cseq = self._cseq_reader.read(song_data)
        required = self.get_required_ids(cseq)
        available = self.get_bank_ids(bank_data, spu_addrs)

        missing = sorted(required - available)
        present = sorted(required & available)
        return ValidationResult(valid=len(missing) == 0, missing_ids=missing, present_ids=present)

    def validate_multi(
        self,
        bank_blobs: list[bytes],
        song_data: bytes,
        spu_addrs: list[SpuAddrEntry],
    ) -> ValidationResult:
        cseq = self._cseq_reader.read(song_data)
        required = self.get_required_ids(cseq)
        available: set[int] = set()

        for blob in bank_blobs:
            available |= self.get_bank_ids(blob, spu_addrs)

        missing = sorted(required - available)
        present = sorted(required & available)
        return ValidationResult(valid=len(missing) == 0, missing_ids=missing, present_ids=present)

    def get_required_ids(self, cseq: CseqFile) -> set[int]:
        ids: set[int] = set()

        for inst in cseq.instruments:
            ids.add(inst.sample_id)

        for perc in cseq.percussions:
            ids.add(perc.sample_id)

        return ids

    def get_bank_ids(self, bank_data: bytes, spu_addrs: list[SpuAddrEntry]) -> set[int]:
        samples = self._bank_reader.parse(bank_data, spu_addrs)
        return {s.spu_index for s in samples}
