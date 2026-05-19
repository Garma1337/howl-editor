# coding: utf-8

"""Stats strip shown above the category grid: a row of small cards each
displaying one HowlFile-level metric (version, bank / song counts, FX,
SPU usage, payload size)."""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from howl_editor.ctr.analysis.howl_stats import HowlStats
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.gui.stylesheet_loader import StylesheetLoader


@dataclass(frozen=True)
class _Cell:
    label: str
    icon: str


_CELLS: tuple[_Cell, ...] = (
    _Cell("VERSION", "🏷️"),
    _Cell("BANKS",   "📚"),
    _Cell("SONGS",   "🎵"),
    _Cell("FX",      "🔊"),
    _Cell("SAMPLES", "🧠"),
    _Cell("PAYLOAD", "💾"),
)


class HowlStatsWidget(QFrame):

    def __init__(
        self,
        size_formatter: SizeFormatter,
        stylesheet_loader: StylesheetLoader,
    ):
        super().__init__()
        self._sizes = size_formatter
        self._values: dict[str, QLabel] = {}
        self._hints: dict[str, QLabel] = {}
        self.setObjectName("howlStats")
        self.setStyleSheet(stylesheet_loader.load("howl_stats.qss"))
        self._build_ui()

    def show_stats(self, stats: HowlStats) -> None:
        for cell, (value_text, hint_text, hint_kind) in zip(_CELLS, self._cell_data(stats)):
            self._values[cell.label].setText(value_text)
            self._set_hint(self._hints[cell.label], hint_text, hint_kind)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        for cell in _CELLS:
            layout.addWidget(self._build_cell(cell), stretch=1)

    def _build_cell(self, cell: _Cell) -> QFrame:
        frame = QFrame()
        frame.setObjectName("howlStatsCell")

        col = QVBoxLayout(frame)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        icon = QLabel(cell.icon)
        icon.setObjectName("howlStatsIcon")
        header.addWidget(icon)

        label = QLabel(cell.label)
        label.setObjectName("howlStatsLabel")
        label.setAlignment(Qt.AlignVCenter)
        header.addWidget(label, stretch=1)

        col.addLayout(header)

        value = QLabel("—")
        value.setObjectName("howlStatsValue")
        col.addWidget(value)

        hint = QLabel("")
        hint.setObjectName("howlStatsHint")
        col.addWidget(hint)

        self._values[cell.label] = value
        self._hints[cell.label] = hint
        return frame

    def _set_hint(self, label: QLabel, text: str, kind: str) -> None:
        label.setText(text)
        # Switching objectName re-applies the matching stylesheet selector so
        # "Modified" / "growth" hints can pick up their accent colors.
        label.setObjectName({
            "modified": "howlStatsHintModified",
            "growth":   "howlStatsHintGrowth",
        }.get(kind, "howlStatsHint"))
        # Force a style re-polish after the objectName change.
        label.style().unpolish(label)
        label.style().polish(label)

    def _cell_data(self, stats: HowlStats) -> list[tuple[str, str, str]]:
        return [
            (stats.version_name,                                       "",                                    "neutral"),
            (str(stats.bank_count),                                    self._modified_hint(stats.modified_bank_count), self._modified_kind(stats.modified_bank_count)),
            (str(stats.song_count),                                    self._modified_hint(stats.modified_song_count), self._modified_kind(stats.modified_song_count)),
            (f"{stats.other_fx_count} + {stats.engine_fx_count}",      "other + engine",                      "neutral"),
            (self._sizes.format_bytes(stats.sample_bytes),             f"{stats.sample_entry_count} entries",  "neutral"),
            (self._sizes.format_bytes(stats.payload_bytes),            self._payload_hint(stats),             self._payload_kind(stats)),
        ]

    def _modified_hint(self, count: int) -> str:
        return f"{count} modified" if count else "unchanged"

    def _modified_kind(self, count: int) -> str:
        return "modified" if count else "neutral"

    def _payload_hint(self, stats: HowlStats) -> str:
        if stats.original_payload_bytes is None:
            return ""

        delta = stats.payload_bytes - stats.original_payload_bytes
        if delta == 0:
            return "= original"

        sign = "+" if delta > 0 else "−"
        return f"{sign}{self._sizes.format_bytes(abs(delta))} vs original"

    def _payload_kind(self, stats: HowlStats) -> str:
        if stats.original_payload_bytes is None:
            return "neutral"

        # Calling out growth specifically — a HOWL that grew past its disc
        # sector budget won't fit at flash time, so make it visually pop.
        if stats.payload_bytes > stats.original_payload_bytes:
            return "growth"

        return "neutral"
