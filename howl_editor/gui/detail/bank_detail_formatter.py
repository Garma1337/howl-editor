# coding: utf-8

from struct import unpack_from

from howl_editor.core.template_engine import TemplateEngine
from howl_editor.ctr.formats.bank.reader import BankReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.gui.size_formatter import SizeFormatter


class BankDetailFormatter:

    def __init__(
        self,
        bank_reader: BankReader,
        template_engine: TemplateEngine,
        size_formatter: SizeFormatter,
    ):
        self._bank_reader = bank_reader
        self._template_engine = template_engine
        self._sizes = size_formatter

    def format_summary(self, hwl: HowlFile) -> str:
        total = sum(len(b) for b in hwl.banks)
        banks = [
            {
                "index": str(i),
                "samples": str(self._bank_sample_count(bank)),
                "size": self._sizes.format_bytes(len(bank)),
                "name": self._bank_reader.get_name(i),
            }
            for i, bank in enumerate(hwl.banks)
        ]

        body = self._template_engine.render(
            "bank_summary.html",
            count=str(len(hwl.banks)),
            total_bytes=f"{total:,}",
            total_kb=f"{total / 1024:.1f}",
            banks=banks,
        )

        return self._template_engine.render("document.html", body=body)

    def format_tree_info(self, bank_data: bytes) -> str:
        size = self._sizes.format_bytes(len(bank_data))
        ns = self._bank_sample_count(bank_data)

        if ns > 0:
            return f"{ns} samples, {size}"

        return size

    def format_details(self, hwl: HowlFile, index: int) -> str:
        bank = hwl.banks[index]
        name = self._bank_reader.get_name(index)
        title = f"Bank {index}" + (f" - {name}" if name else "")

        samples = []
        sample_count = ""
        sample_ids = ""

        if len(bank) >= 2:
            ns = unpack_from("<H", bank, 0)[0]

            if ns < 1024 and len(bank) >= 2 + ns * 2:
                ids = [unpack_from("<h", bank, 2 + i * 2)[0] for i in range(ns)]
                sample_count = str(ns)
                sample_ids = str(ids)

                for i, sid in enumerate(ids):
                    if 0 <= sid < len(hwl.spu_addrs):
                        e = hwl.spu_addrs[sid]
                        samples.append({
                            "index": str(i), "spu_id": str(sid),
                            "size": str(e.size),
                            "bytes": self._sizes.format_bytes(e.byte_size),
                        })
                    else:
                        samples.append({"index": str(i), "spu_id": str(sid), "size": "?", "bytes": "?"})

        body = self._template_engine.render(
            "bank_details.html",
            title=title,
            size=self._sizes.format_bytes(len(bank)),
            samples=samples,
            sample_count=sample_count,
            sample_ids=sample_ids,
        )

        return self._template_engine.render("document.html", body=body)

    def format_sample_details(
        self, hwl: HowlFile, bank_index: int, sample_index: int,
        sample_types: dict[int, set], type_labeler=None,
    ) -> str:
        try:
            samples = self._bank_reader.parse(hwl.banks[bank_index], hwl.spu_addrs)
            if sample_index >= len(samples):
                body = "<p>Sample not found</p>"
                return self._template_engine.render("document.html", body=body)

            sample = samples[sample_index]
        except Exception:
            body = "<p>Failed to parse bank</p>"
            return self._template_engine.render("document.html", body=body)

        types = sample_types.get(sample.spu_index, set())
        classification = type_labeler(types) if type_labeler and types else ""
        bank_name = self._bank_reader.get_name(bank_index)
        bank_label = f"{bank_index}" + (f" - {bank_name}" if bank_name else "")

        body = self._template_engine.render(
            "sample_details.html",
            spu_index=str(sample.spu_index),
            data_size=self._sizes.format_bytes(len(sample.data)),
            bank_label=bank_label,
            position=str(sample_index),
            classification=classification,
        )

        return self._template_engine.render("document.html", body=body)

    def _bank_sample_count(self, data: bytes) -> int:
        if len(data) < 2:
            return 0

        count = unpack_from("<H", data, 0)[0]
        return count if count < 1024 else 0
