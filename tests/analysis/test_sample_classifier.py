# coding: utf-8

from howl_editor.models import (
    HowlFile, SpuAddrEntry, OtherFX, EngineFX,
    CseqInstrument, CseqPercussion,
)
from howl_editor.analysis.sample_classifier import SampleClassifier, SampleType
from tests.conftest import build_cseq_bytes


class TestClassify:
    def test_other_fx_classified_as_sfx(self, sample_classifier):
        hwl = HowlFile(
            other_fx=[OtherFX(flags=0, volume=255, pitch=1024, spu_index=10, duration=100)],
        )
        result = sample_classifier.classify(hwl)
        assert SampleType.SOUND_EFFECT in result[10]

    def test_instrument_classified(self, sample_classifier):
        song = build_cseq_bytes(instruments=[CseqInstrument(sample_id=42)])
        hwl = HowlFile(songs=[song])
        result = sample_classifier.classify(hwl)
        assert SampleType.INSTRUMENT in result[42]

    def test_percussion_classified(self, sample_classifier):
        song = build_cseq_bytes(percussions=[CseqPercussion(sample_id=7)])
        hwl = HowlFile(songs=[song])
        result = sample_classifier.classify(hwl)
        assert SampleType.PERCUSSION in result[7]

    def test_multi_type_sample(self, sample_classifier):
        song = build_cseq_bytes(instruments=[CseqInstrument(sample_id=5)])
        hwl = HowlFile(
            other_fx=[OtherFX(flags=0, volume=255, pitch=1024, spu_index=5, duration=50)],
            songs=[song],
        )
        result = sample_classifier.classify(hwl)
        assert SampleType.INSTRUMENT in result[5]
        assert SampleType.SOUND_EFFECT in result[5]

    def test_empty_hwl(self, sample_classifier):
        hwl = HowlFile()
        result = sample_classifier.classify(hwl)
        assert result == {}

    def test_bad_song_data_skipped(self, sample_classifier):
        hwl = HowlFile(
            other_fx=[OtherFX(flags=0, volume=255, pitch=1024, spu_index=1, duration=10)],
            songs=[b"\xFF\xFF"],
        )
        result = sample_classifier.classify(hwl)
        assert 1 in result


class TestGetLabel:
    def test_empty(self, sample_classifier):
        assert sample_classifier.get_label(set()) == ""

    def test_single(self, sample_classifier):
        assert sample_classifier.get_label({SampleType.INSTRUMENT}) == "Instrument"

    def test_multiple_sorted(self, sample_classifier):
        label = sample_classifier.get_label({SampleType.SOUND_EFFECT, SampleType.INSTRUMENT})
        assert label == "Instrument, SoundEffect"
