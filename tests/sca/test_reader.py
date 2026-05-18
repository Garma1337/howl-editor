# coding: utf-8

from struct import pack

import pytest

from howl_editor.models import ScaFile, ScaFormat, ScaMetadata
from howl_editor.sca.chunk_reader import ScaChunk
from howl_editor.sca.reader import ScaReader


def _make_chunk(tag: bytes, body: bytes) -> bytes:
    raw = tag + pack("<I", len(body)) + body
    pad = (-len(body)) & 3
    return raw + b"\x00" * pad


def _make_sca_bytes(
    bank: bytes = b"\xAA\xBB",
    cseq: bytes = b"\xCC\xDD",
    sizes: list[int] | None = None,
    name: str = "Track",
    author: str = "Author",
    extra_chunks: bytes = b"",
) -> bytes:
    if sizes is None:
        sizes = [10, 20]

    raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
    raw += _make_chunk(ScaFormat.TAG_BANK, bank)
    raw += _make_chunk(ScaFormat.TAG_CSEQ, cseq)
    raw += _make_chunk(ScaFormat.TAG_SIZE, pack(f"<{len(sizes)}H", *sizes))
    meta_body = f'{{"name": "{name}", "author": "{author}"}}'.encode("utf-8")
    raw += _make_chunk(ScaFormat.TAG_META, meta_body)
    raw += extra_chunks

    return bytes(raw)


class TestHappyPath:

    def test_round_trip_with_writer(self, sca_reader, sca_writer):
        original = ScaFile(
            bank=b"\x10\x20\x30",
            cseq=b"\x40\x50\x60\x70",
            sample_sizes=[100, 200, 300],
            metadata=ScaMetadata(name="Round Trip", author="Tester"),
        )

        parsed = sca_reader.parse(sca_writer.serialize(original))

        assert parsed.bank == original.bank
        assert parsed.cseq == original.cseq
        assert parsed.sample_sizes == original.sample_sizes
        assert parsed.metadata == original.metadata

    def test_parses_minimal_well_formed_file(self, sca_reader):
        raw = _make_sca_bytes(bank=b"B", cseq=b"C", sizes=[7], name="N", author="A")
        result = sca_reader.parse(raw)

        assert result.bank == b"B"
        assert result.cseq == b"C"
        assert result.sample_sizes == [7]
        assert result.metadata == ScaMetadata(name="N", author="A")


class TestHeaderValidation:

    def test_rejects_invalid_magic(self, sca_reader):
        raw = bytearray(_make_sca_bytes())
        raw[:3] = b"XCA"

        with pytest.raises(ValueError, match="invalid SCA magic"):
            sca_reader.parse(bytes(raw))

    def test_rejects_unsupported_version(self, sca_reader):
        raw = bytearray(_make_sca_bytes())
        raw[3] = 99

        with pytest.raises(ValueError, match="unsupported SCA version"):
            sca_reader.parse(bytes(raw))

    def test_rejects_file_smaller_than_header(self, sca_reader):
        with pytest.raises(ValueError, match="file too small"):
            sca_reader.parse(b"SC")


class TestRequiredChunks:

    def test_rejects_missing_bank(self, sca_reader):
        raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
        raw += _make_chunk(ScaFormat.TAG_CSEQ, b"C")
        raw += _make_chunk(ScaFormat.TAG_SIZE, b"")
        raw += _make_chunk(ScaFormat.TAG_META, b'{"name":"n","author":"a"}')

        with pytest.raises(ValueError, match="BANK"):
            sca_reader.parse(bytes(raw))

    def test_rejects_missing_cseq(self, sca_reader):
        raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
        raw += _make_chunk(ScaFormat.TAG_BANK, b"B")
        raw += _make_chunk(ScaFormat.TAG_SIZE, b"")
        raw += _make_chunk(ScaFormat.TAG_META, b'{"name":"n","author":"a"}')

        with pytest.raises(ValueError, match="CSEQ"):
            sca_reader.parse(bytes(raw))

    def test_rejects_missing_size(self, sca_reader):
        raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
        raw += _make_chunk(ScaFormat.TAG_BANK, b"B")
        raw += _make_chunk(ScaFormat.TAG_CSEQ, b"C")
        raw += _make_chunk(ScaFormat.TAG_META, b'{"name":"n","author":"a"}')

        with pytest.raises(ValueError, match="SIZE"):
            sca_reader.parse(bytes(raw))

    def test_rejects_missing_meta(self, sca_reader):
        raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
        raw += _make_chunk(ScaFormat.TAG_BANK, b"B")
        raw += _make_chunk(ScaFormat.TAG_CSEQ, b"C")
        raw += _make_chunk(ScaFormat.TAG_SIZE, b"")

        with pytest.raises(ValueError, match="META"):
            sca_reader.parse(bytes(raw))


class TestSizeChunkDecoding:

    def test_decodes_little_endian_u16_array(self, sca_reader):
        raw = _make_sca_bytes(sizes=[0x0102, 0x0304, 0xFFFE])

        assert sca_reader.parse(raw).sample_sizes == [0x0102, 0x0304, 0xFFFE]

    def test_rejects_size_chunk_with_odd_byte_count(self, sca_reader):
        raw = bytearray(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))
        raw += _make_chunk(ScaFormat.TAG_BANK, b"B")
        raw += _make_chunk(ScaFormat.TAG_CSEQ, b"C")
        raw += _make_chunk(ScaFormat.TAG_SIZE, b"\x01\x02\x03")  # 3 bytes -> not u16-aligned
        raw += _make_chunk(ScaFormat.TAG_META, b'{"name":"n","author":"a"}')

        with pytest.raises(ValueError, match="u16 array"):
            sca_reader.parse(bytes(raw))


class TestForwardCompat:

    def test_unknown_chunks_are_skipped(self, sca_reader):
        raw = _make_sca_bytes(extra_chunks=_make_chunk(b"FUTR", b"\xDE\xAD\xBE\xEF"))

        # Must not raise; result should still parse the known chunks.
        result = sca_reader.parse(raw)
        assert result.bank == b"\xAA\xBB"
        assert result.cseq == b"\xCC\xDD"


class TestDependencyInjection:

    def test_uses_injected_chunk_reader(self, sca_metadata_codec):
        # A fake chunk reader proves the orchestrator delegates iteration.
        class FakeChunkReader:
            def __init__(self):
                self.calls: list[int] = []

            def iter_chunks(self, raw, start):
                self.calls.append(start)
                yield ScaChunk(tag=ScaFormat.TAG_BANK, body=b"B")
                yield ScaChunk(tag=ScaFormat.TAG_CSEQ, body=b"C")
                yield ScaChunk(tag=ScaFormat.TAG_SIZE, body=b"")
                yield ScaChunk(tag=ScaFormat.TAG_META, body=b'{"name":"n","author":"a"}')

        fake = FakeChunkReader()
        reader = ScaReader(fake, sca_metadata_codec)
        reader.parse(ScaFormat.MAGIC + bytes([ScaFormat.VERSION]))

        assert fake.calls == [ScaFormat.FILE_HEADER_SIZE]

    def test_uses_injected_metadata_codec(self, sca_chunk_reader):
        # A fake codec proves the orchestrator passes META bytes through.
        class RecordingMetadataCodec:
            def __init__(self):
                self.decoded: list[bytes] = []

            def decode(self, raw):
                self.decoded.append(raw)
                return ScaMetadata(name="from-fake", author="codec")

        recorder = RecordingMetadataCodec()
        reader = ScaReader(sca_chunk_reader, recorder)
        result = reader.parse(_make_sca_bytes(name="ignored", author="ignored"))

        assert len(recorder.decoded) == 1
        assert result.metadata == ScaMetadata(name="from-fake", author="codec")
