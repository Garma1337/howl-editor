# coding: utf-8

from tests.conftest import build_vag_bytes


class TestVagReader:
    def test_reads_headered_vag(self, vag_reader):
        raw = b"\xAA" * 32
        data = build_vag_bytes(data=raw, sample_rate=22050, name="kick")
        sample = vag_reader.read(data)
        assert sample.sample_rate == 22050
        assert sample.name == "kick"
        assert sample.data == raw

    def test_reads_headerless_vag(self, vag_reader):
        raw = b"\xBB" * 64
        sample = vag_reader.read(raw)
        assert sample.data == raw
        assert sample.sample_rate == 44100

    def test_detects_header(self, vag_reader):
        data = build_vag_bytes()
        assert vag_reader._has_header(data)

    def test_no_header_for_short_data(self, vag_reader):
        assert not vag_reader._has_header(b"\x00" * 10)

    def test_no_header_for_wrong_magic(self, vag_reader):
        data = b"NOPE" + b"\x00" * 100
        assert not vag_reader._has_header(data)
