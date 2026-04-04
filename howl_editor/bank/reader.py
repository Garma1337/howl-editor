# coding: utf-8

from struct import unpack_from

from howl_editor.constants import SECTOR_SIZE, bytes_to_sectors
from howl_editor.models import SpuAddrEntry, BankSample


class BankReader:

    def parse(self, bank_data: bytes, spu_addrs: list[SpuAddrEntry]) -> list[BankSample]:
        """
        Parse a bank blob into individual samples.
        Requires the global SPU address table for sample sizes.
        """
        num_samples = self._read_sample_count(bank_data)
        if num_samples == 0:
            return []

        sample_ids = self._read_sample_ids(bank_data, num_samples)
        data_offset = self._calculate_data_offset(num_samples)
        
        return self._extract_samples(bank_data, sample_ids, spu_addrs, data_offset)

    def _read_sample_count(self, data: bytes) -> int:
        if len(data) < 2:
            return 0
        
        count = unpack_from("<H", data, 0)[0]
        return count if count < 1024 else 0

    def _read_sample_ids(self, data: bytes, count: int) -> list[int]:
        ids = []
        for i in range(count):
            offset = 2 + i * 2

            if offset + 2 > len(data):
                break

            sid = unpack_from("<h", data, offset)[0]
            ids.append(sid)

        return ids

    def _calculate_data_offset(self, num_samples: int) -> int:
        header_bytes = 2 + num_samples * 2
        return bytes_to_sectors(header_bytes) * SECTOR_SIZE

    def _extract_samples(
        self,
        data: bytes,
        sample_ids: list[int],
        spu_addrs: list[SpuAddrEntry],
        data_offset: int,
    ) -> list[BankSample]:
        samples = []
        pos = data_offset
        for sid in sample_ids:
            if sid < 0 or sid >= len(spu_addrs):
                continue

            size = spu_addrs[sid].byte_size
            if pos + size <= len(data):
                samples.append(BankSample(spu_index=sid, data=data[pos:pos + size]))
            
            pos += size
        
        return samples
