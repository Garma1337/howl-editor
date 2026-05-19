# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget

from howl_editor.ctr.analysis.howl_stats import HowlStats
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.entries.semantic_entry import EntryGroup
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.category_card_widget import CategoryCardWidget
from howl_editor.gui.widget.howl_stats_widget import HowlStatsWidget

_CARDS_PER_ROW = 4


class CategoryGridWidget(QWidget):
    """The Main tab's default page: a stats strip + a responsive grid of category cards."""

    sig_category_clicked = Signal(object)  # EntryGroup

    def __init__(
        self,
        stylesheet_loader: StylesheetLoader,
        icon_resolver: CategoryIconResolver,
        size_formatter: SizeFormatter,
    ):
        super().__init__()
        self._stylesheets = stylesheet_loader
        self._icon_resolver = icon_resolver
        self._size_formatter = size_formatter
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stats = HowlStatsWidget(self._size_formatter, self._stylesheets)
        outer.addWidget(self._stats)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(self._scroll, stretch=1)

        self._inner = QWidget()
        self._grid = QGridLayout(self._inner)
        self._grid.setContentsMargins(24, 20, 24, 24)
        self._grid.setSpacing(14)
        self._scroll.setWidget(self._inner)

    def show_stats(self, stats: HowlStats) -> None:
        self._stats.show_stats(stats)

    def populate(self, groups: list[EntryGroup], modified_counts: dict[str, int]) -> None:
        self._clear()

        for index, group in enumerate(groups):
            row = index // _CARDS_PER_ROW
            col = index % _CARDS_PER_ROW

            card = CategoryCardWidget(
                group, modified_counts.get(group.name, 0),
                self._stylesheets, self._icon_resolver,
            )
            card.sig_clicked.connect(self.sig_category_clicked)
            self._grid.addWidget(card, row, col)

        # Add a stretch row at the bottom so cards don't expand to fill height.
        self._grid.setRowStretch(self._grid.rowCount(), 1)

    def _clear(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()

            if w is not None:
                w.deleteLater()
