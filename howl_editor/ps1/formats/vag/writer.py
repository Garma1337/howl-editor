# coding: utf-8

from pathlib import Path

from howl_editor.ps1.formats.vag import format as fmt
from howl_editor.ps1.formats.vag.models import VagSample


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
            header, 0, VagSample.MAGIC, fmt.VERSION, 0, len(sample.data), sample.sample_rate,
        )

        name_bytes = sample.name.encode("ascii")[:fmt.NAME_LENGTH]
        header[fmt.NAME_OFFSET:fmt.NAME_OFFSET + len(name_bytes)] = name_bytes

        return bytes(header)
