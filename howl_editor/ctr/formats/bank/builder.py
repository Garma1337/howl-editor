# coding: utf-8

from pathlib import Path
from struct import pack

from howl_editor.ctr.diagnostics.spu_slot_guard import SpuSlotGuard
from howl_editor.ctr.formats.bank.models import BankSample, BankBuildResult
from howl_editor.ctr.formats.howl.models import SpuAddrEntry
from howl_editor.ps1.constants import SECTOR_SIZE, bytes_to_sectors
from howl_editor.ps1.formats.vag.models import VagSample
from howl_editor.ps1.formats.vag.reader import VagReader


class BankBuilder:

    def __init__(self, vag_reader: VagReader, slot_guard: SpuSlotGuard):
        self._vag_reader = vag_reader
        self._slot_guard = slot_guard

    def build_from_files(
        self,
        vag_paths: list[str | Path],
        spu_addrs: list[SpuAddrEntry],
        indices: list[int] | None = None,
    ) -> BankBuildResult:
        """Build a bank blob from VAG files on disk, one sample per slot in
        `indices` (default: appended after the current table). Extends
        spu_addrs with new entries."""
        samples = [self._vag_reader.read_file(p) for p in vag_paths]

        if indices is None:
            return self.build_from_samples(samples, spu_addrs, len(spu_addrs))

        return self.build_at(samples, spu_addrs, indices)

    def build_from_samples(
        self,
        samples: list[VagSample],
        spu_addrs: list[SpuAddrEntry],
        start_index: int,
    ) -> BankBuildResult:
        """Build a bank from VagSample objects into consecutive slots from
        start_index. Extends spu_addrs in place."""
        return self.build_at(samples, spu_addrs, list(range(start_index, start_index + len(samples))))

    def build_at(
        self,
        samples: list[VagSample],
        spu_addrs: list[SpuAddrEntry],
        indices: list[int],
    ) -> BankBuildResult:
        """Build a bank from VagSample objects, sample i going into slot
        indices[i]. Existing slots are resized; missing ones are appended."""
        if len(indices) != len(samples):
            raise ValueError(f"{len(samples)} samples but {len(indices)} slots")

        self._slot_guard.ensure_creatable(spu_addrs, indices)

        for idx, sample in zip(indices, samples):
            self._ensure_spu_addr(spu_addrs, idx, len(sample.data))

        blob = self._assemble_blob(list(indices), [s.data for s in samples])

        return BankBuildResult(
            bank_data=blob,
            new_spu_indices=list(indices),
            sample_rates=[s.sample_rate for s in samples],
        )

    def build_from_raw(self, sample_data: list[tuple[int, bytes]]) -> bytes:
        """Build a bank from pre-indexed (spu_index, raw_data) pairs."""
        indices = [sid for sid, _ in sample_data]
        datas = [d for _, d in sample_data]
        return self._assemble_blob(indices, datas)

    def merge(self, samples: list[BankSample]) -> bytes:
        return self._assemble_blob(
            [s.spu_index for s in samples],
            [s.data for s in samples],
        )

    def remove_sample(
        self,
        bank_data: bytes,
        spu_addrs: list[SpuAddrEntry],
        sample_index: int,
        bank_reader: 'BankReader',
    ) -> bytes:
        samples = bank_reader.parse(bank_data, spu_addrs)
        if sample_index < 0 or sample_index >= len(samples):
            raise IndexError(f"Sample index {sample_index} out of range (0..{len(samples) - 1})")

        del samples[sample_index]
        return self.merge(samples)

    def add_sample(
        self,
        bank_data: bytes,
        spu_addrs: list[SpuAddrEntry],
        new_data: bytes,
        bank_reader: 'BankReader',
        spu_index: int | None = None,
    ) -> bytes:
        """If spu_index is None, the new sample appends an SPU table entry."""
        samples = bank_reader.parse(bank_data, spu_addrs)

        if spu_index is None:
            spu_index = len(spu_addrs)

        self._slot_guard.ensure_creatable(spu_addrs, [spu_index])
        self._ensure_spu_addr(spu_addrs, spu_index, len(new_data))
        samples.append(BankSample(spu_index=spu_index, data=new_data))
        return self.merge(samples)

    def replace_sample(
        self,
        bank_data: bytes,
        spu_addrs: list[SpuAddrEntry],
        sample_index: int,
        new_data: bytes,
        bank_reader: 'BankReader',
    ) -> bytes:
        """Also updates the SPU address table entry with the new size."""
        samples = bank_reader.parse(bank_data, spu_addrs)
        if sample_index < 0 or sample_index >= len(samples):
            raise IndexError(f"Sample index {sample_index} out of range (0..{len(samples) - 1})")

        spu_id = samples[sample_index].spu_index
        samples[sample_index] = BankSample(spu_index=spu_id, data=new_data)
        self._ensure_spu_addr(spu_addrs, spu_id, len(new_data))
        return self.merge(samples)

    def _ensure_spu_addr(self, spu_addrs: list[SpuAddrEntry], index: int, data_len: int) -> None:
        while len(spu_addrs) <= index:
            spu_addrs.append(SpuAddrEntry(0, 0))

        spu_addrs[index] = SpuAddrEntry(0, data_len // 8)

    def _assemble_blob(self, indices: list[int], datas: list[bytes]) -> bytes:
        header = self._build_header(indices)
        padded = self._pad_to_sector(header)
        body = b"".join(datas)
        
        return padded + body

    def _build_header(self, indices: list[int]) -> bytes:
        out = pack("<H", len(indices))
        for idx in indices:
            out += pack("<h", idx)
        
        return out

    def _pad_to_sector(self, data: bytes) -> bytes:
        padded_len = bytes_to_sectors(len(data)) * SECTOR_SIZE
        return data + b"\x00" * (padded_len - len(data))
