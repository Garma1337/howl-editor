# coding: utf-8

import pytest
from howl_editor.vlq import read_vlq, write_vlq


class TestReadVlq:
    def test_zero(self):
        val, pos = read_vlq(b"\x00", 0)
        assert val == 0
        assert pos == 1

    def test_single_byte(self):
        val, pos = read_vlq(b"\x7F", 0)
        assert val == 127
        assert pos == 1

    def test_two_bytes(self):
        val, pos = read_vlq(b"\x81\x00", 0)
        assert val == 128
        assert pos == 2

    def test_large_value(self):
        # 0xFF 0x7F = (0x7F << 7) | 0x7F = 16383
        val, pos = read_vlq(b"\xFF\x7F", 0)
        assert val == 16383

    def test_offset(self):
        val, pos = read_vlq(b"\xAA\xBB\x05\xCC", 2)
        assert val == 5
        assert pos == 3

    def test_unterminated_raises(self):
        with pytest.raises(ValueError, match="Unterminated"):
            read_vlq(b"\x80", 0)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            read_vlq(b"", 0)


class TestWriteVlq:
    def test_zero(self):
        assert write_vlq(0) == b"\x00"

    def test_single_byte(self):
        assert write_vlq(127) == b"\x7F"

    def test_two_bytes(self):
        assert write_vlq(128) == b"\x81\x00"

    def test_large_value(self):
        assert write_vlq(16383) == b"\xFF\x7F"

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            write_vlq(-1)


class TestVlqRoundTrip:
    @pytest.mark.parametrize("value", [0, 1, 63, 127, 128, 255, 16383, 16384, 65535, 1000000])
    def test_round_trip(self, value):
        encoded = write_vlq(value)
        decoded, _ = read_vlq(encoded, 0)
        assert decoded == value
