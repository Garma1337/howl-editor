# coding: utf-8

from struct import pack

from howl_editor.saphi.formats.sca.chunk_writer import ScaChunkWriter
from howl_editor.saphi.formats.sca.metadata_codec import ScaMetadataCodec
from howl_editor.saphi.formats.sca.models import ScaFile, ScaFormat, ScaMetadata


class ScaWriter:
    """Serializes a ScaFile into .sca container bytes."""

    def __init__(self, chunk_writer: ScaChunkWriter, metadata_codec: ScaMetadataCodec):
        self._chunks = chunk_writer
        self._metadata = metadata_codec

    def serialize(self, sca: ScaFile) -> bytes:
        out = bytearray()
        self._write_header(out)
        self._write_bank(out, sca.bank)
        self._write_cseq(out, sca.cseq)
        self._write_sizes(out, sca.sample_sizes)
        self._write_metadata(out, sca.metadata)

        return bytes(out)

    def _write_header(self, out: bytearray) -> None:
        out += ScaFormat.MAGIC
        out += pack("<B", ScaFormat.VERSION)

    def _write_bank(self, out: bytearray, bank: bytes) -> None:
        self._chunks.write(out, ScaFormat.TAG_BANK, bank)

    def _write_cseq(self, out: bytearray, cseq: bytes) -> None:
        self._chunks.write(out, ScaFormat.TAG_CSEQ, cseq)

    def _write_sizes(self, out: bytearray, sizes: list[int]) -> None:
        body = pack(f"<{len(sizes)}H", *sizes)
        self._chunks.write(out, ScaFormat.TAG_SIZE, body)

    def _write_metadata(self, out: bytearray, metadata: ScaMetadata) -> None:
        body = self._metadata.encode(metadata)
        self._chunks.write(out, ScaFormat.TAG_META, body)
