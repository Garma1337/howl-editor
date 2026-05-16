# coding: utf-8

from dataclasses import dataclass
from struct import unpack_from

from howl_editor.models import ScaFormat


@dataclass
class ScaChunk:
    tag: bytes
    body: bytes


class ScaChunkReader:
    """Walks a .sca byte buffer one [tag | bodySize | body | zero-pad] chunk at a time."""

    def iter_chunks(self, raw: bytes, start: int):
        pos = start
        while pos < len(raw):
            if len(raw) - pos < ScaFormat.CHUNK_HEADER_SIZE:
                raise ValueError(f"truncated chunk header at offset {pos}")

            tag = bytes(raw[pos:pos + ScaFormat.CHUNK_TAG_SIZE])
            body_size = unpack_from("<I", raw, pos + ScaFormat.CHUNK_TAG_SIZE)[0]
            body_off = pos + ScaFormat.CHUNK_HEADER_SIZE

            if body_size > len(raw) - body_off:
                raise ValueError(f"chunk {tag!r} at offset {pos} body extends past end of file")

            yield ScaChunk(tag=tag, body=bytes(raw[body_off:body_off + body_size]))

            pos = body_off + body_size + ((-body_size) & (ScaFormat.CHUNK_ALIGNMENT - 1))
