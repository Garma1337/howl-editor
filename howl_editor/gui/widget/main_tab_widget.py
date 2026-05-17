# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel, QStackedWidget, QVBoxLayout, QWidget,
)

from howl_editor.analysis.entry_leaves import EntryLeavesBuilder
from howl_editor.analysis.semantic_entries import SemanticEntryBuilder
from howl_editor.cseq.adventure_hub import AdventureHubMaskTable
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.category_detail_widget import CategoryDetailWidget
from howl_editor.gui.widget.category_grid_widget import CategoryGridWidget
from howl_editor.howl.blob_snapshot import BlobSnapshot
from howl_editor.models import EntryGroup, HowlFile


_PAGE_EMPTY = 0
_PAGE_GRID = 1
_PAGE_DETAIL = 2


class MainTabWidget(QWidget):
    """Card-grid + drill-down navigation for in-game entries.

    Default = category grid. Clicking a category swaps to its detail view
    showing every entry's leaves (sequences / samples) with per-leaf Play.
    """

    sig_row_replace = Signal(object)         # EntryRow
    sig_row_export = Signal(object)
    sig_row_reset = Signal(object)
    sig_row_play = Signal(object)            # only used by FX entries
    sig_row_drop = Signal(object, str)

    sig_leaf_play = Signal(object)           # EntryLeaf
    sig_leaf_replace = Signal(object)
    sig_leaf_export = Signal(object)
    sig_leaf_drop = Signal(object, str)

    sig_play_hub_preview = Signal(int, object, str)

    def __init__(
        self,
        entry_builder: SemanticEntryBuilder,
        leaves_builder: EntryLeavesBuilder,
        snapshot: BlobSnapshot,
        stylesheet_loader: StylesheetLoader,
        hub_mask_table: AdventureHubMaskTable,
        icon_resolver: CategoryIconResolver,
    ):
        super().__init__()
        self._builder = entry_builder
        self._leaves_builder = leaves_builder
        self._snapshot = snapshot
        self._stylesheets = stylesheet_loader
        self._hub_mask = hub_mask_table
        self._icon_resolver = icon_resolver
        self._hwl: HowlFile | None = None
        self._groups: list[EntryGroup] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("mainTabRoot")
        self.setStyleSheet(self._stylesheets.load("main_tab.qss"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._empty_label = QLabel("Open a HWL file to see its in-game entries here.")
        self._empty_label.setObjectName("mainTabEmpty")
        self._stack.addWidget(self._empty_label)

        self._grid = CategoryGridWidget(self._stylesheets, self._icon_resolver)
        self._grid.sig_category_clicked.connect(self._on_category_clicked)
        self._stack.addWidget(self._grid)

        self._detail = CategoryDetailWidget(
            self._leaves_builder, self._snapshot, self._stylesheets,
            self._hub_mask, self._icon_resolver,
        )

        self._detail.sig_back.connect(self._on_back)
        self._detail.sig_replace_parent.connect(self.sig_row_replace)
        self._detail.sig_export_parent.connect(self.sig_row_export)
        self._detail.sig_reset_parent.connect(self.sig_row_reset)
        self._detail.sig_leaf_play.connect(self.sig_leaf_play)
        self._detail.sig_leaf_replace.connect(self.sig_leaf_replace)
        self._detail.sig_leaf_export.connect(self.sig_leaf_export)
        self._detail.sig_leaf_drop.connect(self.sig_leaf_drop)
        self._detail.sig_row_play.connect(self.sig_row_play)
        self._detail.sig_row_replace.connect(self.sig_row_replace)
        self._detail.sig_row_export.connect(self.sig_row_export)
        self._detail.sig_row_drop.connect(self.sig_row_drop)
        self._detail.sig_play_hub_preview.connect(self.sig_play_hub_preview)
        self._stack.addWidget(self._detail)

        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def clear(self) -> None:
        self._hwl = None
        self._groups = []
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def refresh(self, hwl: HowlFile | None) -> None:
        if hwl is None:
            self.clear()
            return

        self._hwl = hwl
        self._groups = self._builder.build(hwl, self._snapshot.banks, self._snapshot.songs)

        if not self._groups:
            self._stack.setCurrentIndex(_PAGE_EMPTY)
            return

        modified = {
            g.name: sum(1 for r in g.rows if r.is_modified)
            for g in self._groups
        }
        self._grid.populate(self._groups, modified)

        if self._stack.currentIndex() == _PAGE_DETAIL:
            current_title = self._detail._title.text()
            match = next((g for g in self._groups if g.name == current_title), None)

            if match is not None:
                self._detail.show_category(hwl, match)
                return

        self._stack.setCurrentIndex(_PAGE_GRID)

    def _on_category_clicked(self, group: EntryGroup) -> None:
        if self._hwl is None:
            return

        self._detail.show_category(self._hwl, group)
        self._stack.setCurrentIndex(_PAGE_DETAIL)

    def _on_back(self) -> None:
        self._stack.setCurrentIndex(_PAGE_GRID)
