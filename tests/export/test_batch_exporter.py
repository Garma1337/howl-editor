# coding: utf-8

import pytest

from howl_editor.analysis.sample_classifier import SampleClassifier
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.audio.wav_writer import WavWriter
from howl_editor.bank.reader import BankReader
from howl_editor.core.vlq import VlqCodec
from howl_editor.cseq.reader import CseqReader
from howl_editor.export.batch_exporter import BatchExporter
from howl_editor.midi.exporter import CseqMidiExporter
from howl_editor.models import (
    HowlFile, SpuAddrEntry, OtherFX,
    CseqInstrument, CseqPercussion,
)
from howl_editor.vag.writer import VagWriter
from tests.conftest import build_cseq_bytes, build_bank_blob


@pytest.fixture
def batch_exporter():
    cseq_reader = CseqReader(VlqCodec())

    return BatchExporter(
        bank_reader=BankReader(),
        cseq_reader=cseq_reader,
        vag_writer=VagWriter(),
        vag_decoder=VagDecoder(WavWriter()),
        sample_classifier=SampleClassifier(cseq_reader),
        midi_exporter=CseqMidiExporter(),
    )


def _make_hwl():
    spu = [SpuAddrEntry(0, 2)] * 10
    bank = build_bank_blob([0, 1], [b"\x00" * 16, b"\x00" * 16])

    song = build_cseq_bytes(
        instruments=[CseqInstrument(sample_id=0)],
        percussions=[CseqPercussion(sample_id=1)],
    )

    return HowlFile(
        spu_addrs=spu,
        other_fx=[OtherFX(flags=0, volume=255, pitch=1024, spu_index=0, duration=50)],
        banks=[bank],
        songs=[song],
    )


class TestBatchExport:

    def test_creates_directories(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        batch_exporter.export(hwl, tmp_path)

        assert (tmp_path / "banks").is_dir()
        assert (tmp_path / "songs").is_dir()
        assert (tmp_path / "samples").is_dir()

    def test_exports_banks(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        result = batch_exporter.export(hwl, tmp_path)
        assert result.banks == 1

        bnk_files = list((tmp_path / "banks").glob("*.bnk"))
        assert len(bnk_files) == 1

    def test_exports_songs(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        result = batch_exporter.export(hwl, tmp_path)
        assert result.songs == 1

        cseq_files = list((tmp_path / "songs").glob("*.cseq"))
        assert len(cseq_files) == 1

    def test_exports_samples_as_vag_and_wav(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        result = batch_exporter.export(hwl, tmp_path)
        assert result.samples == 2

        vag_files = list((tmp_path / "samples").rglob("*.vag"))
        wav_files = list((tmp_path / "samples").rglob("*.wav"))

        assert len(vag_files) == 2
        assert len(wav_files) == 2

    def test_classifies_into_subdirs(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        batch_exporter.export(hwl, tmp_path)

        # Sample 0 is both SFX and Instrument -> instruments/ takes priority
        # Sample 1 is Percussion
        subdirs = [p.name for p in (tmp_path / "samples").iterdir() if p.is_dir()]

        assert len(subdirs) >= 1

    def test_result_counts(self, batch_exporter, tmp_path):
        hwl = _make_hwl()
        result = batch_exporter.export(hwl, tmp_path)

        assert result.banks >= 1
        assert result.songs >= 1
        assert result.samples >= 1

    def test_empty_hwl(self, batch_exporter, tmp_path):
        hwl = HowlFile()
        result = batch_exporter.export(hwl, tmp_path)

        assert result.banks == 0
        assert result.songs == 0
        assert result.samples == 0
