"""Writes VagSample models to VAG file format."""

from pathlib import Path

from howl_editor.constants import VAG_MAGIC, VAG_HEADER_SIZE, VAG_HEADER_STRUCT
from howl_editor.models import VagSample


class VagWriter:

    def serialize(self, sample: VagSample) -> bytes:
        """Serialize a VagSample to VAG file bytes (with header)."""
        header = self._build_header(sample)
        return header + sample.data

    def write_file(self, sample: VagSample, path: str | Path) -> None:
        """Write a VAG file to disk."""
        Path(path).write_bytes(self.serialize(sample))

    def _build_header(self, sample: VagSample) -> bytes:
        header = bytearray(VAG_HEADER_SIZE)
        VAG_HEADER_STRUCT.pack_into(header, 0, VAG_MAGIC, 3, 0, len(sample.data), sample.sample_rate)
        name_bytes = sample.name.encode("ascii")[:16]
        header[0x20:0x20 + len(name_bytes)] = name_bytes
        return bytes(header)
