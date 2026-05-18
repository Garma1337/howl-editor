# coding: utf-8

from struct import unpack_from

from howl_editor.analysis.stock_name_resolver import StockNameResolver
from howl_editor.models import SpuAddrEntry, BankSample
from howl_editor.models.howl import SECTOR_SIZE, bytes_to_sectors

_SAMPLE_COUNT_SIZE = 2
_SAMPLE_ID_SIZE = 2
_MAX_SAMPLE_COUNT = 1024
_SPU_ADDR_BYTE_MULTIPLIER = 8


class BankReader:

    def __init__(self, stock_names: StockNameResolver):
        self._name_resolver = stock_names

    def get_name(self, index: int) -> str:
        return self._name_resolver.bank_name(index)

    def parse(self, bank_data: bytes, spu_addrs: list[SpuAddrEntry]) -> list[BankSample]:
        """Parse a bank blob into individual samples."""
        num_samples = self._read_sample_count(bank_data)
        if num_samples == 0:
            return []

        sample_ids = self._read_sample_ids(bank_data, num_samples)
        data_offset = self._calculate_data_offset(num_samples)

        return self._extract_samples(bank_data, sample_ids, spu_addrs, data_offset)

    def _read_sample_count(self, data: bytes) -> int:
        if len(data) < _SAMPLE_COUNT_SIZE:
            return 0

        count = unpack_from("<H", data, 0)[0]
        return count if count < _MAX_SAMPLE_COUNT else 0

    def _read_sample_ids(self, data: bytes, count: int) -> list[int]:
        ids = []
        for i in range(count):
            offset = _SAMPLE_COUNT_SIZE + i * _SAMPLE_ID_SIZE

            if offset + _SAMPLE_ID_SIZE > len(data):
                break

            sid = unpack_from("<h", data, offset)[0]
            ids.append(sid)

        return ids

    def _calculate_data_offset(self, num_samples: int) -> int:
        header_bytes = _SAMPLE_COUNT_SIZE + num_samples * _SAMPLE_ID_SIZE
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
