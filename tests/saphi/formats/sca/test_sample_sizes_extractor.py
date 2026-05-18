# coding: utf-8

import pytest

from howl_editor.ctr.formats.howl.models import SpuAddrEntry
from howl_editor.saphi.formats.sca.sample_sizes_extractor import SampleSizesExtractor
from tests.conftest import build_bank_blob


@pytest.fixture
def extractor(bank_reader):
    return SampleSizesExtractor(bank_reader)


class TestExtract:

    def test_returns_sizes_in_bank_header_order(self, extractor):
        spu_addrs = [
            SpuAddrEntry(0, 0),     # id 0
            SpuAddrEntry(0, 100),   # id 1
            SpuAddrEntry(0, 200),   # id 2
            SpuAddrEntry(0, 50),    # id 3
        ]
        sample_data = [b"\x00" * 800, b"\x00" * 1600, b"\x00" * 400]
        bank = build_bank_blob([2, 1, 3], sample_data)

        sizes = extractor.extract(bank, spu_addrs)

        assert sizes == [200, 100, 50]

    def test_empty_bank_returns_empty_list(self, extractor):
        spu_addrs = []
        bank = build_bank_blob([], [])

        assert extractor.extract(bank, spu_addrs) == []

    def test_skips_samples_with_out_of_range_ids(self, extractor):
        # BankReader.parse drops samples whose spu_index is out of range, so the
        # extractor's output should match that behavior — sizes count == valid samples.
        spu_addrs = [SpuAddrEntry(0, 100)]   # only id 0 is valid
        sample_data = [b"\x00" * 800, b"\x00" * 800]
        bank = build_bank_blob([0, 99], sample_data)

        sizes = extractor.extract(bank, spu_addrs)

        assert sizes == [100]
