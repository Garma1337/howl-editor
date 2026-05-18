# coding: utf-8

from dataclasses import dataclass
from struct import unpack_from

from howl_editor.ctr.formats.howl.models import HowlHeader
from howl_editor.ctr.formats.howl.versions import KNOWN_VERSIONS


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
        name = KNOWN_VERSIONS.get(version, f"Unknown (0x{version:02X})")

        return VersionInfo(
            version_value=version,
            version_name=name,
            is_known=version in KNOWN_VERSIONS,
            magic_valid=magic_valid,
        )
