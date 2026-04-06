# coding: utf-8

from struct import unpack_from

from howl_editor.bank.reader import BankReader
from howl_editor.models import HowlFile


class BankDetailFormatter:

    def __init__(self, bank_reader: BankReader):
        self._bank_reader = bank_reader

    def format_summary(self, hwl: HowlFile) -> str:
        total = sum(len(b) for b in hwl.banks)
        lines = [
            f"Banks ({len(hwl.banks)})", "=" * 50,
            f"Total: {total:,} bytes ({total / 1024:.1f} KB)", "",
            f"{'Idx':>4}  {'Samples':>8}  {'Size':>10}  Name", "-" * 50,
        ]

        for i, bank in enumerate(hwl.banks):
            ns = self._bank_sample_count(bank)
            name = self._bank_reader.get_name(i)
            label = f"  {name}" if name else ""
            lines.append(f"{i:>4}  {ns:>8}  {len(bank):>10,}{label}")

        return "\n".join(lines)

    def format_tree_info(self, bank_data: bytes) -> str:
        ns = self._bank_sample_count(bank_data)
        if ns > 0:
            return f"{ns} samples, {len(bank_data):,} bytes"

        return f"{len(bank_data):,} bytes"

    def format_details(self, hwl: HowlFile, index: int) -> str:
        bank = hwl.banks[index]
        name = self._bank_reader.get_name(index)
        header = f"Bank {index}" + (f" - {name}" if name else "")
        lines = [header, "=" * 50, f"Size: {len(bank):,} bytes"]

        if len(bank) >= 2:
            ns = unpack_from("<H", bank, 0)[0]
            lines.append(f"Samples: {ns}")

            if ns < 1024 and len(bank) >= 2 + ns * 2:
                ids = [unpack_from("<h", bank, 2 + i * 2)[0] for i in range(ns)]
                lines.append(f"Sample IDs: {ids}")
                lines.append("")
                lines.append(f"{'#':>4}  {'SPU ID':>7}  {'Size':>6}  {'Bytes':>8}")
                lines.append("-" * 35)

                for i, sid in enumerate(ids):
                    if 0 <= sid < len(hwl.spu_addrs):
                        e = hwl.spu_addrs[sid]
                        lines.append(f"{i:>4}  {sid:>7}  {e.size:>6}  {e.byte_size:>8}")
                    else:
                        lines.append(f"{i:>4}  {sid:>7}  {'?':>6}  {'?':>8}")

        return "\n".join(lines)

    def _bank_sample_count(self, data: bytes) -> int:
        if len(data) < 2:
            return 0

        count = unpack_from("<H", data, 0)[0]
        return count if count < 1024 else 0
