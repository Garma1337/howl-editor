# coding: utf-8

from struct import pack

import pytest


def _make_chunk(tag: bytes, body: bytes) -> bytes:
    raw = tag + pack("<I", len(body)) + body
    pad = (-len(body)) & 3
    return raw + b"\x00" * pad


class TestEmptyBuffer:

    def test_no_chunks_when_start_at_end(self, sca_chunk_reader):
        chunks = list(sca_chunk_reader.iter_chunks(b"", 0))

        assert chunks == []


class TestSingleChunk:

    def test_yields_one_chunk_with_correct_tag_and_body(self, sca_chunk_reader):
        raw = _make_chunk(b"BANK", b"\x01\x02\x03")
        chunks = list(sca_chunk_reader.iter_chunks(raw, 0))

        assert len(chunks) == 1
        assert chunks[0].tag == b"BANK"
        assert chunks[0].body == b"\x01\x02\x03"


class TestPaddingAndAlignment:

    def test_advances_past_zero_padding_to_next_4byte_boundary(self, sca_chunk_reader):
        # First chunk body is 3 bytes (1 pad byte), second should still parse cleanly.
        raw = _make_chunk(b"BANK", b"\x01\x02\x03") + _make_chunk(b"CSEQ", b"\xAA\xBB")
        chunks = list(sca_chunk_reader.iter_chunks(raw, 0))

        assert [c.tag for c in chunks] == [b"BANK", b"CSEQ"]
        assert chunks[1].body == b"\xAA\xBB"

    def test_no_padding_added_when_body_is_already_aligned(self, sca_chunk_reader):
        raw = _make_chunk(b"BANK", b"\x01\x02\x03\x04") + _make_chunk(b"CSEQ", b"\xAA")
        chunks = list(sca_chunk_reader.iter_chunks(raw, 0))

        assert [c.tag for c in chunks] == [b"BANK", b"CSEQ"]


class TestStartOffset:

    def test_respects_start_offset_so_caller_can_skip_file_header(self, sca_chunk_reader):
        prefix = b"SCA\x01"  # simulate file header
        raw = prefix + _make_chunk(b"BANK", b"\x42")
        chunks = list(sca_chunk_reader.iter_chunks(raw, len(prefix)))

        assert len(chunks) == 1
        assert chunks[0].tag == b"BANK"
        assert chunks[0].body == b"\x42"


class TestErrors:

    def test_rejects_truncated_chunk_header(self, sca_chunk_reader):
        with pytest.raises(ValueError, match="truncated chunk header"):
            list(sca_chunk_reader.iter_chunks(b"BAN", 0))

    def test_rejects_body_extending_past_end_of_file(self, sca_chunk_reader):
        # Declares 100-byte body but only 2 are present.
        raw = b"BANK" + pack("<I", 100) + b"\x01\x02"
        with pytest.raises(ValueError, match="body extends past end of file"):
            list(sca_chunk_reader.iter_chunks(raw, 0))
