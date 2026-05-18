# coding: utf-8

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr.formats.howl.version import HowlVersionDetector
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.ps1 import spu


class HowlDetailFormatter:

    def __init__(
        self,
        version_detector: HowlVersionDetector,
        template_engine: TemplateEngine,
        size_formatter: SizeFormatter,
    ):
        self._version_detector = version_detector
        self._template_engine = template_engine
        self._sizes = size_formatter

    def format_details(self, hwl: HowlFile, file_path: str | None, raw_data: bytes | None = None) -> str:
        version_str = f"{hwl.version} ({hwl.version:#x})"
        if raw_data:
            info = self._version_detector.detect(raw_data)
            version_str += f" - {info.version_name}"

        rows = [
            {"key": "Version", "value": version_str},
            {"key": "Reserved 1", "value": str(hwl.reserved1)},
            {"key": "Reserved 2", "value": str(hwl.reserved2)},
            {"key": "SPU Entries", "value": str(len(hwl.spu_addrs))},
            {"key": "Effects", "value": str(len(hwl.other_fx))},
            {"key": "Engine FX", "value": str(len(hwl.engine_fx))},
            {"key": "Banks", "value": str(len(hwl.banks))},
            {"key": "Songs", "value": str(len(hwl.songs))},
            {"key": "Header data size", "value": self._sizes.format_bytes(hwl.header_data_size)},
        ]

        total_spu_bytes = sum(e.byte_size for e in hwl.spu_addrs)
        rows.append({
            "key": "SPU usage",
            "value": f"{self._sizes.format_spu_usage(total_spu_bytes, spu.RAM_BYTES)} "
                     f"({self._sizes.percentage(total_spu_bytes, spu.RAM_BYTES):.0f}%)",
        })

        if file_path:
            rows.append({"key": "File", "value": file_path})

        body = self._template_engine.render("howl_details.html", rows=rows)
        return self._template_engine.render("document.html", body=body)

    def format_spu_table(self, hwl: HowlFile) -> str:
        entries = [
            {
                "index": str(i), "ptr": str(e.ptr), "size": str(e.size),
                "bytes": self._sizes.format_bytes(e.byte_size),
            }
            for i, e in enumerate(hwl.spu_addrs)
        ]

        body = self._template_engine.render("spu_table.html", count=str(len(hwl.spu_addrs)), entries=entries)
        return self._template_engine.render("document.html", body=body)
