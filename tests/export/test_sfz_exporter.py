# coding: utf-8

import pytest

from howl_editor.audio.wav_writer import WavWriter
from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.cseq.models import CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile, SpuAddrEntry
from howl_editor.ctr.sample_lookup import SampleLookup
from howl_editor.export.sfz_exporter import SfzExporter
from howl_editor.ps1.formats.vag.decoder import VagDecoder
from tests.conftest import build_cseq_bytes, build_bank_blob


@pytest.fixture
def sfz_exporter():
    bank_reader = BankReader(StockNameResolver())
    cseq_reader = CseqReader(VlqCodec(), StockNameResolver())
    return SfzExporter(
        cseq_reader=cseq_reader,
        bank_reader=bank_reader,
        sample_lookup=SampleLookup(bank_reader, cseq_reader),
        vag_decoder=VagDecoder(WavWriter()),
    )


def _make_hwl():
    spu = [SpuAddrEntry(0, 2)] * 4
    bank = build_bank_blob([0, 1], [b"\x00" * 16, b"\x00" * 16])
    song = build_cseq_bytes(
        instruments=[
            CseqInstrument(volume=255, frequency=0x1000, sample_id=0),
            CseqInstrument(volume=128, frequency=0x2000, sample_id=1),
        ],
        percussions=[CseqPercussion(volume=200, frequency=0x1000, sample_id=0)],
    )

    return HowlFile(spu_addrs=spu, banks=[bank], songs=[song])


class TestSfzExport:

    def test_writes_sfz_text_and_samples(self, sfz_exporter, tmp_path):
        sfz_path = tmp_path / "test.sfz"
        written = sfz_exporter.export(_make_hwl(), 0, sfz_path, wav_sample_rate=22050)

        assert sfz_path.exists()
        assert (tmp_path / "samples").is_dir()
        assert written == 2  # two distinct SPU ids referenced

    def test_sfz_contains_region_per_entry(self, sfz_exporter, tmp_path):
        sfz_path = tmp_path / "test.sfz"
        sfz_exporter.export(_make_hwl(), 0, sfz_path, wav_sample_rate=22050)

        text = sfz_path.read_text(encoding="utf-8")
        # Two instruments + one percussion → at least three <region> blocks.
        assert text.count("<region>") >= 3
        assert "<group>" in text
        assert "samples/SPU_0000.wav" in text
        assert "samples/SPU_0001.wav" in text

    def test_octave_up_frequency_emits_positive_tune(self, sfz_exporter, tmp_path):
        sfz_path = tmp_path / "test.sfz"
        sfz_exporter.export(_make_hwl(), 0, sfz_path, wav_sample_rate=22050)

        text = sfz_path.read_text(encoding="utf-8")
        # Instrument 1 has frequency=0x2000 (one octave up) → tune=1200.
        assert "tune=1200" in text

    def test_safe_filename_stem(self, sfz_exporter):
        assert sfz_exporter.safe_filename_stem("Dingo Canyon") == "Dingo_Canyon"
        assert sfz_exporter.safe_filename_stem("a/b\\c?") == "a_b_c"
        assert sfz_exporter.safe_filename_stem("") == "song"
