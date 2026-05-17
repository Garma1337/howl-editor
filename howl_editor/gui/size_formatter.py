# coding: utf-8


class SizeFormatter:
    """Formats byte counts as human-readable strings (KB, MB) with thousands
    separators. Used in detail panels and bank/sample rows where raw byte counts
    were previously shown."""

    _KB = 1024
    _MB = 1024 * 1024

    def format_bytes(self, byte_count: int) -> str:
        if byte_count < self._KB:
            return f"{byte_count:,} B"

        if byte_count < self._MB:
            return f"{byte_count / self._KB:,.1f} KB"

        return f"{byte_count / self._MB:,.2f} MB"

    def format_spu_usage(self, used_bytes: int, total_bytes: int) -> str:
        return f"{self.format_bytes(used_bytes)} / {self.format_bytes(total_bytes)}"

    def percentage(self, used: int, total: int) -> float:
        if total <= 0:
            return 0.0

        return min(100.0, max(0.0, used / total * 100.0))
