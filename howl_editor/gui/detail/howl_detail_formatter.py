# coding: utf-8

from howl_editor.howl.version import HowlVersionDetector
from howl_editor.models import HowlFile


class HowlDetailFormatter:

    def __init__(self, version_detector: HowlVersionDetector):
        self._version_detector = version_detector

    def format_details(self, hwl: HowlFile, file_path: str | None, raw_data: bytes | None = None) -> str:
        version_str = f"{hwl.version} ({hwl.version:#x})"
        if raw_data:
            info = self._version_detector.detect(raw_data)
            version_str += f" - {info.version_name}"

        lines = [
            "HOWL File", "=" * 40,
            f"Version:     {version_str}",
            f"Reserved 1:  {hwl.reserved1}",
            f"Reserved 2:  {hwl.reserved2}",
            f"SPU Entries:  {len(hwl.spu_addrs)}",
            f"Effects:     {len(hwl.other_fx)}",
            f"Engine FX:   {len(hwl.engine_fx)}",
            f"Banks:       {len(hwl.banks)}",
            f"Songs:       {len(hwl.songs)}",
            f"\nHeader data size: {hwl.header_data_size} bytes",
        ]

        if file_path:
            lines.append(f"File: {file_path}")

        return "\n".join(lines)

    def format_spu_table(self, hwl: HowlFile) -> str:
        lines = [
            f"SPU Address Table ({len(hwl.spu_addrs)} entries)", "=" * 50,
            f"{'Index':>6}  {'Ptr':>6}  {'Size':>6}  {'Bytes':>8}", "-" * 35,
        ]

        for i, e in enumerate(hwl.spu_addrs):
            lines.append(f"{i:>6}  {e.ptr:>6}  {e.size:>6}  {e.byte_size:>8}")

        return "\n".join(lines)
