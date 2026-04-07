# coding: utf-8

import pytest

from howl_editor.core.vlq import VlqCodec


@pytest.fixture
def codec():
    return VlqCodec()


class TestRead:
    def test_zero(self, codec):
        val, pos = codec.read(b"\x00", 0)

        assert val == 0
        assert pos == 1

    def test_single_byte(self, codec):
        val, pos = codec.read(b"\x7F", 0)

        assert val == 127
        assert pos == 1

    def test_two_bytes(self, codec):
        val, pos = codec.read(b"\x81\x00", 0)

        assert val == 128
        assert pos == 2

    def test_large_value(self, codec):
        # 0xFF 0x7F = (0x7F << 7) | 0x7F = 16383
        val, pos = codec.read(b"\xFF\x7F", 0)

        assert val == 16383

    def test_offset(self, codec):
        val, pos = codec.read(b"\xAA\xBB\x05\xCC", 2)

        assert val == 5
        assert pos == 3

    def test_unterminated_raises(self, codec):
        with pytest.raises(ValueError, match="Unterminated"):
            codec.read(b"\x80", 0)

    def test_empty_raises(self, codec):
        with pytest.raises(ValueError):
            codec.read(b"", 0)


class TestWrite:

    def test_zero(self, codec):
        assert codec.write(0) == b"\x00"

    def test_single_byte(self, codec):
        assert codec.write(127) == b"\x7F"

    def test_two_bytes(self, codec):
        assert codec.write(128) == b"\x81\x00"

    def test_large_value(self, codec):
        assert codec.write(16383) == b"\xFF\x7F"

    def test_negative_raises(self, codec):
        with pytest.raises(ValueError, match="non-negative"):
            codec.write(-1)


class TestRoundTrip:
    @pytest.mark.parametrize("value", [0, 1, 63, 127, 128, 255, 16383, 16384, 65535, 1000000])
    def test_round_trip(self, value):
        codec = VlqCodec()
        encoded = codec.write(value)
        decoded, _ = codec.read(encoded, 0)
        assert decoded == value
