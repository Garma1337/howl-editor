# coding: utf-8

from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry, OtherFX, EngineFX
from howl_editor.ctr.sample_lookup import SampleLookup
from tests.conftest import build_bank_blob, build_cseq_bytes


def _lookup():
    return SampleLookup(BankReader(StockNameResolver()), CseqReader(VlqCodec(), StockNameResolver()))


def _hwl_with_sample(spu_index=0, data=b"\x00" * 16):
    blob = build_bank_blob([spu_index], [data])
    return HowlFile(
        spu_addrs=[SpuAddrEntry(0, len(data) // 8)],
        banks=[blob],
    )


class TestFindSampleData:

    def test_finds_sample_in_bank(self):
        hwl = _hwl_with_sample(spu_index=0, data=b"\xAB" * 16)
        result = _lookup().find_sample_data(hwl, 0)

        assert result == b"\xAB" * 16

    def test_returns_none_for_missing_spu(self):
        hwl = _hwl_with_sample(spu_index=0)
        result = _lookup().find_sample_data(hwl, 99)

        assert result is None

    def test_returns_none_for_empty_hwl(self):
        hwl = HowlFile()
        result = _lookup().find_sample_data(hwl, 0)

        assert result is None

    def test_searches_multiple_banks(self):
        blob1 = build_bank_blob([0], [b"\x11" * 16])
        blob2 = build_bank_blob([1], [b"\x22" * 16])
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 2), SpuAddrEntry(0, 2)],
            banks=[blob1, blob2],
        )

        assert _lookup().find_sample_data(hwl, 1) == b"\x22" * 16


class TestFindBankAndSampleIndex:

    def test_resolves_to_first_matching_bank_and_slot(self):
        blob = build_bank_blob([0, 1, 2], [b"\xAA" * 16, b"\xBB" * 16, b"\xCC" * 16])
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 2)] * 3,
            banks=[blob],
        )

        assert _lookup().find_bank_and_sample_index(hwl, 1) == (0, 1)

    def test_returns_none_when_spu_not_in_any_bank(self):
        hwl = _hwl_with_sample(spu_index=0)
        assert _lookup().find_bank_and_sample_index(hwl, 99) is None

    def test_returns_first_bank_when_spu_duplicated(self):
        # When two banks both contain the same spu_index, we return the
        # earlier bank — this matches find_sample_data's first-match policy.
        blob_a = build_bank_blob([5], [b"\x11" * 16])
        blob_b = build_bank_blob([5], [b"\x22" * 16])
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 2)] * 6,
            banks=[blob_a, blob_b],
        )

        bank_index, slot = _lookup().find_bank_and_sample_index(hwl, 5)
        assert bank_index == 0
        assert slot == 0

    def test_returns_none_for_empty_hwl(self):
        hwl = HowlFile()
        assert _lookup().find_bank_and_sample_index(hwl, 0) is None


class TestCollectSongSamples:

    def test_collects_instrument_samples(self):
        blob = build_bank_blob([5], [b"\xCC" * 16])
        hwl = HowlFile(
            spu_addrs=[SpuAddrEntry(0, 0)] * 5 + [SpuAddrEntry(0, 2)],
            banks=[blob],
        )
        cseq_data = build_cseq_bytes(instruments=[CseqInstrument(sample_id=5)])
        cseq = CseqReader(VlqCodec(), StockNameResolver()).read(cseq_data)
        result = _lookup().collect_song_samples(hwl, cseq)

        assert 5 in result
        assert result[5] == b"\xCC" * 16

    def test_empty_when_no_banks(self):
        hwl = HowlFile()
        cseq_data = build_cseq_bytes(instruments=[CseqInstrument(sample_id=0)])
        cseq = CseqReader(VlqCodec(), StockNameResolver()).read(cseq_data)
        result = _lookup().collect_song_samples(hwl, cseq)

        assert result == {}


class TestLookupSampleRate:

    def test_finds_rate_from_other_fx(self):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=5, pitch=4096)])
        rate = _lookup().lookup_sample_rate(hwl, 5)

        assert rate == 44100

    def test_finds_rate_from_engine_fx(self):
        hwl = HowlFile(engine_fx=[EngineFX(spu_index=3, pitch=2048)])
        rate = _lookup().lookup_sample_rate(hwl, 3)

        assert rate == 22050

    def test_finds_rate_from_instrument(self):
        cseq_data = build_cseq_bytes(instruments=[CseqInstrument(sample_id=7, frequency=4096)])
        hwl = HowlFile(songs=[cseq_data])
        rate = _lookup().lookup_sample_rate(hwl, 7)

        assert rate == 44100

    def test_finds_rate_from_percussion(self):
        cseq_data = build_cseq_bytes(percussions=[CseqPercussion(sample_id=10, frequency=2048)])
        hwl = HowlFile(songs=[cseq_data])
        rate = _lookup().lookup_sample_rate(hwl, 10)

        assert rate == 22050

    def test_returns_default_when_not_found(self):
        hwl = HowlFile()
        rate = _lookup().lookup_sample_rate(hwl, 99)

        assert rate == 11025

    def test_other_fx_takes_priority_over_instruments(self):
        cseq_data = build_cseq_bytes(instruments=[CseqInstrument(sample_id=5, frequency=2048)])
        hwl = HowlFile(
            other_fx=[OtherFX(spu_index=5, pitch=4096)],
            songs=[cseq_data],
        )
        rate = _lookup().lookup_sample_rate(hwl, 5)

        # OtherFX is checked first → 44100, not 22050
        assert rate == 44100

    def test_skips_zero_pitch(self):
        hwl = HowlFile(other_fx=[OtherFX(spu_index=5, pitch=0)])
        rate = _lookup().lookup_sample_rate(hwl, 5)

        assert rate == 11025
