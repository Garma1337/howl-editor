# coding: utf-8

from struct import pack

from howl_editor.models import ScaFormat


class ScaChunkWriter:
    """Appends a single SCA chunk: [tag | bodySize | body | zero-pad to alignment]."""

    def write(self, out: bytearray, tag: bytes, body: bytes) -> None:
        if len(tag) != ScaFormat.CHUNK_TAG_SIZE:
            raise ValueError(f"chunk tag must be {ScaFormat.CHUNK_TAG_SIZE} bytes, got {len(tag)}: {tag!r}")

        out += tag
        out += pack("<I", len(body))
        out += body
        self._pad_to_alignment(out)

    def _pad_to_alignment(self, out: bytearray) -> None:
        remainder = len(out) % ScaFormat.CHUNK_ALIGNMENT
        if remainder:
            out += b"\x00" * (ScaFormat.CHUNK_ALIGNMENT - remainder)
