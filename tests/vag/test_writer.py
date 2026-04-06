# coding: utf-8

from struct import unpack_from

from howl_editor.constants import VAG_MAGIC, VAG_HEADER_SIZE
from howl_editor.models import VagSample


class TestVagWriter:
    def test_produces_header(self, vag_writer):
        sample = VagSample(sample_rate=11025, name="snare", data=b"\x01" * 16)
        data = vag_writer.serialize(sample)
        assert data[:4] == VAG_MAGIC
        assert len(data) == VAG_HEADER_SIZE + 16

    def test_header_fields(self, vag_writer):
        sample = VagSample(sample_rate=22050, data=b"\x00" * 32)
        data = vag_writer.serialize(sample)
        _, version, _, data_size, sample_rate = unpack_from(">4sIIII", data, 0)
        assert version == 3
        assert data_size == 32
        assert sample_rate == 22050

    def test_name_in_header(self, vag_writer):
        sample = VagSample(name="myinst", data=b"\x00" * 16)
        data = vag_writer.serialize(sample)
        name = data[0x20:0x26]
        assert name == b"myinst"


class TestVagRoundTrip:
    def test_roundtrip(self, vag_reader, vag_writer):
        original = VagSample(sample_rate=44100, name="test", data=b"\xDE\xAD" * 20)
        serialized = vag_writer.serialize(original)
        parsed = vag_reader.read(serialized)
        assert parsed.sample_rate == original.sample_rate
        assert parsed.name == original.name
        assert parsed.data == original.data
