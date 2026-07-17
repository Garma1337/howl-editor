# coding: utf-8

from howl_editor.ps1.formats.vag import format as fmt
from howl_editor.ps1.formats.vag.structure_validator import VagStructureValidator


def _frame(flags: int, header: int = 0x20) -> bytes:
    return bytes([header, flags]) + b"\x11" * (fmt.FRAME_SIZE - 2)


def _sample(*flag_bytes: int) -> bytes:
    return b"".join(_frame(f) for f in flag_bytes)


class TestWellFormed:
    """Every stock CTR sample is frame-aligned, uses only legal flag bytes and
    ends on a terminator. A slice that fails any of those was cut at the wrong
    offset, which is the only thing this is asked to detect."""

    def test_plain_one_shot_is_valid(self):
        result = VagStructureValidator().validate(_sample(0, 0, fmt.FLAG_LOOP_END))

        assert result.is_valid
        assert result.frame_count == 3

    def test_end_of_data_sentinel_is_a_terminator(self):
        assert VagStructureValidator().validate(_sample(0, fmt.FLAG_END_OF_DATA)).is_valid

    def test_looping_sample_is_valid(self):
        data = _sample(fmt.FLAG_LOOP_START, 0, fmt.FLAG_LOOP_END | fmt.FLAG_LOOP_REPEAT)

        assert VagStructureValidator().validate(data).is_valid


class TestMisalignedSlice:

    def test_missing_terminator_is_rejected(self):
        # A slice cut short stops mid-sample, so no end marker is present.
        result = VagStructureValidator().validate(_sample(0, 0, 0))

        assert not result.is_valid
        assert result.terminates is False

    def test_flag_byte_landing_on_payload_is_rejected(self):
        # Offset slices put the flag byte on ADPCM data, which exceeds 0x07.
        result = VagStructureValidator().validate(_sample(0, 0x9C, fmt.FLAG_LOOP_END))

        assert not result.is_valid
        assert result.invalid_flag_frame == 1

    def test_reports_the_first_bad_frame_only(self):
        result = VagStructureValidator().validate(_sample(0, 0x40, 0x80, fmt.FLAG_LOOP_END))

        assert result.invalid_flag_frame == 1

    def test_partial_frame_is_not_aligned(self):
        result = VagStructureValidator().validate(_sample(fmt.FLAG_LOOP_END) + b"\x00\x00\x00")

        assert not result.is_valid
        assert result.frame_aligned is False

    def test_empty_slice_is_not_valid(self):
        result = VagStructureValidator().validate(b"")

        assert not result.is_valid
        assert result.frame_count == 0
