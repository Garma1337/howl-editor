# coding: utf-8

from struct import unpack_from

import pytest

from howl_editor.models import ScaFile, ScaMetadata
from howl_editor.sca.writer import ScaWriter


def _make_sca(bank: bytes = b"\x01\x02", cseq: bytes = b"\x03\x04",
              sizes: list[int] | None = None, name: str = "Track", author: str = "Author") -> ScaFile:
    return ScaFile(
        bank=bank,
        cseq=cseq,
        sample_sizes=sizes if sizes is not None else [],
        metadata=ScaMetadata(name=name, author=author),
    )


class TestHeader:

    def test_starts_with_magic_and_version(self, sca_writer):
        out = sca_writer.serialize(_make_sca())

        assert out[0:3] == b"SCA"
        assert out[3] == 1


class TestChunkOrder:

    def test_chunks_appear_in_documented_order(self, sca_writer):
        out = sca_writer.serialize(_make_sca(
            bank=b"\xAA" * 4,
            cseq=b"\xBB" * 4,
            sizes=[10, 20],
            name="N",
            author="A",
        ))

        # Walk the file: skip header (4 bytes), then check each chunk tag in order.
        positions = []
        pos = 4
        while pos < len(out):
            tag = bytes(out[pos:pos+4])
            size = unpack_from("<I", out, pos+4)[0]
            positions.append(tag)
            pos += 4 + 4 + size
            pad = (-size) & 3
            pos += pad

        assert positions == [b"BANK", b"CSEQ", b"SIZE", b"META"]


class TestSizeChunk:

    def test_size_chunk_body_is_two_bytes_per_entry(self, sca_writer):
        sca = _make_sca(sizes=[1, 2, 3])
        out = sca_writer.serialize(sca)

        # Find SIZE chunk
        pos = _find_chunk(out, b"SIZE")
        body_size = unpack_from("<I", out, pos+4)[0]

        assert body_size == 6  # 3 entries * 2 bytes

    def test_size_chunk_entries_are_little_endian_u16(self, sca_writer):
        sca = _make_sca(sizes=[0x0102, 0x0304])
        out = sca_writer.serialize(sca)
        pos = _find_chunk(out, b"SIZE")
        body = bytes(out[pos+8:pos+8+4])

        assert body == b"\x02\x01\x04\x03"

    def test_empty_sample_sizes_emits_zero_length_size_chunk(self, sca_writer):
        out = sca_writer.serialize(_make_sca(sizes=[]))
        pos = _find_chunk(out, b"SIZE")

        assert unpack_from("<I", out, pos+4)[0] == 0


class TestBankAndCseqChunks:

    def test_bank_chunk_carries_exact_bytes(self, sca_writer):
        bank_bytes = b"\xDE\xAD\xBE\xEF\xCA\xFE"
        out = sca_writer.serialize(_make_sca(bank=bank_bytes))
        pos = _find_chunk(out, b"BANK")
        body_size = unpack_from("<I", out, pos+4)[0]

        assert bytes(out[pos+8:pos+8+body_size]) == bank_bytes

    def test_cseq_chunk_carries_exact_bytes(self, sca_writer):
        cseq_bytes = b"\xAA\xBB\xCC"
        out = sca_writer.serialize(_make_sca(cseq=cseq_bytes))
        pos = _find_chunk(out, b"CSEQ")
        body_size = unpack_from("<I", out, pos+4)[0]

        assert bytes(out[pos+8:pos+8+body_size]) == cseq_bytes


class TestMetadataChunk:

    def test_meta_chunk_contains_name_and_author(self, sca_writer):
        out = sca_writer.serialize(_make_sca(name="Breeze Harbor", author="Garma"))
        pos = _find_chunk(out, b"META")
        body_size = unpack_from("<I", out, pos+4)[0]
        body = bytes(out[pos+8:pos+8+body_size]).decode("utf-8")

        assert "Breeze Harbor" in body
        assert "Garma" in body


class TestDependencyInjection:

    def test_writer_delegates_each_chunk_to_chunk_writer(self, sca_metadata_codec):
        # A recording fake captures all calls so we can assert composition,
        # not just final bytes — proves ScaWriter doesn't bypass its collaborator.
        class RecordingChunkWriter:
            def __init__(self):
                self.calls: list[tuple[bytes, bytes]] = []
            def write(self, out, tag, body):
                self.calls.append((tag, body))
                out += tag

        recorder = RecordingChunkWriter()
        writer = ScaWriter(recorder, sca_metadata_codec)
        writer.serialize(_make_sca(bank=b"B", cseq=b"C", sizes=[7]))

        tags = [tag for tag, _ in recorder.calls]
        assert tags == [b"BANK", b"CSEQ", b"SIZE", b"META"]

    def test_writer_uses_injected_metadata_codec(self, sca_chunk_writer):
        # A fake codec lets us verify the writer passes the right metadata in,
        # without depending on JSON-specific output bytes.
        class RecordingMetadataCodec:
            def __init__(self):
                self.encoded: list[ScaMetadata] = []
            def encode(self, metadata):
                self.encoded.append(metadata)
                return b"<encoded>"

        recorder = RecordingMetadataCodec()
        writer = ScaWriter(sca_chunk_writer, recorder)
        writer.serialize(_make_sca(name="X", author="Y"))

        assert recorder.encoded == [ScaMetadata(name="X", author="Y")]


class TestRoundTrip:

    def test_serialize_and_manually_parse_matches_input(self, sca_writer, sca_metadata_codec):
        sca = _make_sca(
            bank=b"\x10\x20\x30",
            cseq=b"\x40\x50\x60\x70\x80",
            sizes=[100, 200, 300],
            name="Round Trip",
            author="Tester",
        )
        out = sca_writer.serialize(sca)

        chunks = _parse_all_chunks(out)
        assert chunks[b"BANK"] == sca.bank
        assert chunks[b"CSEQ"] == sca.cseq
        assert chunks[b"SIZE"] == b"\x64\x00\xC8\x00\x2C\x01"  # 100, 200, 300 LE u16
        assert sca_metadata_codec.decode(chunks[b"META"]) == sca.metadata


def _find_chunk(out: bytes, tag: bytes) -> int:
    """Returns the byte offset of the chunk header for `tag` (start of the 4-byte tag field)."""
    pos = 4  # skip file header
    while pos < len(out):
        if bytes(out[pos:pos+4]) == tag:
            return pos
        size = unpack_from("<I", out, pos+4)[0]
        pos += 4 + 4 + size
        pos += (-size) & 3  # pad to 4-byte boundary

    raise AssertionError(f"chunk {tag!r} not found")


def _parse_all_chunks(out: bytes) -> dict[bytes, bytes]:
    """Returns a {tag: body} dict by walking all chunks after the file header."""
    chunks: dict[bytes, bytes] = {}
    pos = 4
    while pos < len(out):
        tag = bytes(out[pos:pos+4])
        size = unpack_from("<I", out, pos+4)[0]
        chunks[tag] = bytes(out[pos+8:pos+8+size])
        pos += 4 + 4 + size + ((-size) & 3)

    return chunks
