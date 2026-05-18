# coding: utf-8

from struct import unpack_from

import pytest


class TestWrite:

    def test_empty_body_emits_tag_and_zero_size(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"BANK", b"")

        assert bytes(out[0:4]) == b"BANK"
        assert unpack_from("<I", out, 4)[0] == 0
        assert len(out) == 8  # tag(4) + size(4), no body, no pad needed

    def test_aligned_body_emits_no_pad(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"SIZE", b"\x01\x02\x03\x04")

        assert bytes(out[0:4]) == b"SIZE"
        assert unpack_from("<I", out, 4)[0] == 4
        assert bytes(out[8:12]) == b"\x01\x02\x03\x04"
        assert len(out) == 12

    def test_one_byte_body_emits_three_pad_bytes(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"BANK", b"\xAA")

        assert bytes(out[8:9]) == b"\xAA"
        assert bytes(out[9:12]) == b"\x00\x00\x00"
        assert len(out) == 12

    def test_five_byte_body_emits_three_pad_bytes(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"CSEQ", b"\xAA\xBB\xCC\xDD\xEE")

        assert bytes(out[8:13]) == b"\xAA\xBB\xCC\xDD\xEE"
        assert bytes(out[13:16]) == b"\x00\x00\x00"
        assert len(out) == 16

    def test_six_byte_body_emits_two_pad_bytes(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"META", b"\x01\x02\x03\x04\x05\x06")

        assert bytes(out[14:16]) == b"\x00\x00"
        assert len(out) == 16

    def test_seven_byte_body_emits_one_pad_byte(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"META", b"\x01\x02\x03\x04\x05\x06\x07")

        assert bytes(out[15:16]) == b"\x00"
        assert len(out) == 16

    def test_appends_to_existing_buffer(self, sca_chunk_writer):
        out = bytearray(b"\xFF\xFF\xFF\xFF")
        sca_chunk_writer.write(out, b"BANK", b"\xAA")

        assert bytes(out[0:4]) == b"\xFF\xFF\xFF\xFF"
        assert bytes(out[4:8]) == b"BANK"
        assert unpack_from("<I", out, 8)[0] == 1
        assert bytes(out[12:13]) == b"\xAA"

    def test_back_to_back_chunks_stay_aligned(self, sca_chunk_writer):
        out = bytearray()
        sca_chunk_writer.write(out, b"BANK", b"\xAA")
        sca_chunk_writer.write(out, b"CSEQ", b"\xBB\xCC")

        assert len(out) % 4 == 0
        assert bytes(out[12:16]) == b"CSEQ"

    @pytest.mark.parametrize("bad_tag", [b"", b"BA", b"BAN", b"BANKS", b"X" * 10])
    def test_wrong_tag_length_raises(self, sca_chunk_writer, bad_tag):
        out = bytearray()

        with pytest.raises(ValueError, match="chunk tag must be"):
            sca_chunk_writer.write(out, bad_tag, b"")
