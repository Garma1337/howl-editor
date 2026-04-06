# coding: utf-8

from pathlib import Path

from howl_editor.models import VagSample

_VAG_VERSION = 3
_MAX_NAME_LENGTH = 16
_NAME_OFFSET = 0x20


class VagWriter:

    def serialize(self, sample: VagSample) -> bytes:
        """Serialize a VagSample to VAG file bytes (with header)."""
        header = self._build_header(sample)
        return header + sample.data

    def write_file(self, sample: VagSample, path: str | Path) -> None:
        """Write a VAG file to disk."""
        Path(path).write_bytes(self.serialize(sample))

    def _build_header(self, sample: VagSample) -> bytes:
        header = bytearray(VagSample.HEADER_SIZE)
        VagSample.HEADER_STRUCT.pack_into(
            header, 0, VagSample.MAGIC, _VAG_VERSION, 0, len(sample.data), sample.sample_rate,
        )
        name_bytes = sample.name.encode("ascii")[:_MAX_NAME_LENGTH]
        header[_NAME_OFFSET:_NAME_OFFSET + len(name_bytes)] = name_bytes
        return bytes(header)
