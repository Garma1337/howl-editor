# coding: utf-8

from howl_editor.models import SpuAddrEntry, CseqInstrument, CseqPercussion
from howl_editor.analysis.validator import ValidationResult
from tests.conftest import build_cseq_bytes, build_bank_blob


class TestValidationResult:
    def test_valid_message(self):
        r = ValidationResult(valid=True, present_ids=[1, 2, 3])
        assert "Valid" in r.message
        assert "3" in r.message

    def test_invalid_message(self):
        r = ValidationResult(valid=False, missing_ids=[5, 10], present_ids=[1, 2])
        assert "missing" in r.message
        assert "SPU 5" in r.message
        assert "SPU 10" in r.message
        assert "2 of 4" in r.message


class TestValidate:
    def test_all_present(self, validator):
        spu = [SpuAddrEntry(0, 2)] * 10
        bank = build_bank_blob([3, 5], [b"\x00" * 16, b"\x00" * 16])
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=3)],
            percussions=[CseqPercussion(sample_id=5)],
        )
        result = validator.validate(bank, song, spu)
        assert result.valid is True
        assert result.missing_ids == []

    def test_missing_sample(self, validator):
        spu = [SpuAddrEntry(0, 2)] * 10
        bank = build_bank_blob([3], [b"\x00" * 16])
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=3), CseqInstrument(sample_id=7)],
        )
        result = validator.validate(bank, song, spu)
        assert result.valid is False
        assert 7 in result.missing_ids
        assert 3 in result.present_ids

    def test_empty_cseq(self, validator):
        spu = [SpuAddrEntry(0, 2)] * 5
        bank = build_bank_blob([0], [b"\x00" * 16])
        song = build_cseq_bytes(instruments=[], percussions=[])
        result = validator.validate(bank, song, spu)
        assert result.valid is True


class TestValidateMulti:
    def test_samples_across_banks(self, validator):
        spu = [SpuAddrEntry(0, 2)] * 10
        bank1 = build_bank_blob([3], [b"\x00" * 16])
        bank2 = build_bank_blob([7], [b"\x00" * 16])
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=3), CseqInstrument(sample_id=7)],
        )
        result = validator.validate_multi([bank1, bank2], song, spu)
        assert result.valid is True

    def test_still_missing(self, validator):
        spu = [SpuAddrEntry(0, 2)] * 10
        bank1 = build_bank_blob([3], [b"\x00" * 16])
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=3), CseqInstrument(sample_id=9)],
        )
        result = validator.validate_multi([bank1], song, spu)
        assert result.valid is False
        assert 9 in result.missing_ids


class TestGetRequiredIds:
    def test_collects_from_instruments_and_percussions(self, validator, cseq_reader):
        song = build_cseq_bytes(
            instruments=[CseqInstrument(sample_id=1), CseqInstrument(sample_id=2)],
            percussions=[CseqPercussion(sample_id=3)],
        )
        cseq = cseq_reader.read(song)
        ids = validator.get_required_ids(cseq)
        assert ids == {1, 2, 3}
