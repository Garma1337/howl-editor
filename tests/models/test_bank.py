# coding: utf-8

from howl_editor.models import BankSample, BankBuildResult


class TestBankSample:

    def test_creation(self):
        s = BankSample(spu_index=42, data=b"\xFF")

        assert s.spu_index == 42
        assert s.data == b"\xFF"


class TestBankBuildResult:

    def test_creation(self):
        r = BankBuildResult(bank_data=b"\x00", new_spu_indices=[10, 11])

        assert r.bank_data == b"\x00"
        assert r.new_spu_indices == [10, 11]
