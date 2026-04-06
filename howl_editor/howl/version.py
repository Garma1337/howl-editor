# coding: utf-8

from dataclasses import dataclass
from struct import unpack_from

from howl_editor.models import HowlHeader

_KNOWN_VERSIONS: dict[int, str] = {
    0x6F: "Demo (Test Drive)",
    0x71: "Demo (OPSM)",
    0x72: "Demo (Spyro)",
    0x78: "Beta (Aug 5)",
    0x7D: "Prototype",
    0x80: "Release",
}


@dataclass
class VersionInfo:
    version_value: int
    version_name: str
    is_known: bool
    magic_valid: bool


class HowlVersionDetector:

    def detect(self, data: bytes) -> VersionInfo:
        if len(data) < HowlHeader.SIZE:
            return VersionInfo(0, "Invalid", False, False)

        magic = unpack_from("<I", data, 0)[0]
        version = unpack_from("<I", data, 4)[0]
        magic_valid = magic == HowlHeader.MAGIC
        name = _KNOWN_VERSIONS.get(version, f"Unknown (0x{version:02X})")

        return VersionInfo(
            version_value=version,
            version_name=name,
            is_known=version in _KNOWN_VERSIONS,
            magic_valid=magic_valid,
        )
