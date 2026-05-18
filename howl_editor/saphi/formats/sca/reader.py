# coding: utf-8

from struct import unpack_from

from howl_editor.saphi.formats.sca.chunk_reader import ScaChunkReader
from howl_editor.saphi.formats.sca.metadata_codec import ScaMetadataCodec
from howl_editor.saphi.formats.sca.models import ScaFile, ScaFormat


class ScaReader:
    """Parses .sca container bytes into a ScaFile."""

    def __init__(self, chunk_reader: ScaChunkReader, metadata_codec: ScaMetadataCodec):
        self._chunks = chunk_reader
        self._metadata = metadata_codec

    def parse(self, raw: bytes) -> ScaFile:
        self._validate_header(raw)

        bank = None
        cseq = None
        sample_sizes = None
        metadata = None

        for chunk in self._chunks.iter_chunks(raw, ScaFormat.FILE_HEADER_SIZE):
            if chunk.tag == ScaFormat.TAG_BANK:
                bank = chunk.body
            elif chunk.tag == ScaFormat.TAG_CSEQ:
                cseq = chunk.body
            elif chunk.tag == ScaFormat.TAG_SIZE:
                sample_sizes = self._decode_sizes(chunk.body)
            elif chunk.tag == ScaFormat.TAG_META:
                metadata = self._metadata.decode(chunk.body)
            # Unknown tags are skipped for forward compatibility.

        self._require(bank is not None, "missing required BANK chunk")
        self._require(cseq is not None, "missing required CSEQ chunk")
        self._require(sample_sizes is not None, "missing required SIZE chunk")
        self._require(metadata is not None, "missing required META chunk")

        return ScaFile(bank=bank, cseq=cseq, sample_sizes=sample_sizes, metadata=metadata)

    def _validate_header(self, raw: bytes) -> None:
        if len(raw) < ScaFormat.FILE_HEADER_SIZE:
            raise ValueError(f"file too small for SCA header: {len(raw)} < {ScaFormat.FILE_HEADER_SIZE}")

        if raw[:len(ScaFormat.MAGIC)] != ScaFormat.MAGIC:
            raise ValueError(f"invalid SCA magic: {raw[:len(ScaFormat.MAGIC)]!r}, expected {ScaFormat.MAGIC!r}")

        version = raw[len(ScaFormat.MAGIC)]
        if version != ScaFormat.VERSION:
            raise ValueError(f"unsupported SCA version: {version}, expected {ScaFormat.VERSION}")

    def _decode_sizes(self, body: bytes) -> list[int]:
        if len(body) % 2 != 0:
            raise ValueError(f"SIZE chunk body must be a u16 array, got {len(body)} bytes")

        n = len(body) // 2
        return list(unpack_from(f"<{n}H", body, 0))

    def _require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)
