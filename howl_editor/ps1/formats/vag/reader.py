# coding: utf-8

from pathlib import Path

from howl_editor.ps1.formats.vag import format as fmt
from howl_editor.ps1.formats.vag.models import VagSample


class VagReader:

    def read(self, data: bytes) -> VagSample:
        """Parse VAG bytes. Handles both headered and headerless data."""
        if self._has_header(data):
            return self._read_with_header(data)

        return VagSample(data=data)

    def read_file(self, path: str | Path) -> VagSample:
        """Read a VAG file from disk."""
        return self.read(Path(path).read_bytes())

    def _has_header(self, data: bytes) -> bool:
        return len(data) >= VagSample.HEADER_SIZE and data[:4] == VagSample.MAGIC

    def _read_with_header(self, data: bytes) -> VagSample:
        _, version, _, data_size, sample_rate = VagSample.HEADER_STRUCT.unpack_from(data, 0)
        name = data[fmt.NAME_OFFSET:fmt.NAME_OFFSET + fmt.NAME_LENGTH].split(b"\x00")[0].decode("ascii", errors="replace")
        raw = data[VagSample.HEADER_SIZE:]
        return VagSample(sample_rate=sample_rate, name=name, data=raw)
