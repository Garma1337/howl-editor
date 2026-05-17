# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from howl_editor.analysis.entry_leaves import EntryLeavesBuilder
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.entry_parent_widget import EntryParentWidget
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget
from howl_editor.howl.blob_snapshot import BlobSnapshot
from howl_editor.models import EntryGroup, HowlFile, LeafKind, EntryLeaf
from howl_editor.models.semantic_entry import EntryKind, EntryRow


class CategoryDetailWidget(QWidget):
    """The Main tab's per-category page: back button + entries with leaves."""

    sig_back = Signal()
    sig_replace_parent = Signal(object)
    sig_export_parent = Signal(object)
    sig_reset_parent = Signal(object)
    sig_leaf_play = Signal(object)
    sig_leaf_replace = Signal(object)
    sig_leaf_export = Signal(object)
    sig_leaf_drop = Signal(object, str)
    sig_row_play = Signal(object)             # for FX entries that ARE leaves
    sig_row_replace = Signal(object)
    sig_row_export = Signal(object)
    sig_row_drop = Signal(object, str)

    def __init__(
        self,
        leaves_builder: EntryLeavesBuilder,
        snapshot: BlobSnapshot,
        stylesheet_loader: StylesheetLoader,
    ):
        super().__init__()
        self._leaves_builder = leaves_builder
        self._snapshot = snapshot
        self._stylesheets = stylesheet_loader
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(self._stylesheets.load("category_detail.qss"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = self._build_header()
        outer.addWidget(self._header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(self._scroll, stretch=1)

        self._scroll_inner = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_inner)
        self._scroll_layout.setContentsMargins(24, 12, 24, 24)
        self._scroll_layout.setSpacing(8)
        self._scroll_layout.addStretch(1)
        self._scroll.setWidget(self._scroll_inner)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("categoryDetailHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 14, 20, 6)
        layout.setSpacing(12)

        back = QPushButton("←  Categories")
        back.setObjectName("backButton")
        back.setFixedWidth(130)
        back.clicked.connect(self.sig_back)
        layout.addWidget(back)

        self._title_icon = QLabel()
        self._title_icon.setObjectName("detailIcon")
        layout.addWidget(self._title_icon)

        self._title = QLabel()
        self._title.setObjectName("detailTitle")
        layout.addWidget(self._title, stretch=1)

        return header

    def show_category(self, hwl: HowlFile, group: EntryGroup) -> None:
        self._title.setText(group.name)
        self._title_icon.setText(group.icon)
        self._render_entries(hwl, group)

    def _render_entries(self, hwl: HowlFile, group: EntryGroup) -> None:
        self._clear_content()
        can_reset = self._snapshot.has_snapshot()

        single_entry_category = len(group.rows) <= 1

        for row in group.rows:
            # FX entries are themselves single playable units; render as a flat
            # leaf-style row that emits row-level signals.
            if row.kind in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX):
                self._insert_widget(self._build_fx_row(row))
                continue

            leaves = self._leaves_builder.build(hwl, row)
            parent = EntryParentWidget(
                row, leaves, group.icon, self._stylesheets,
                can_reset=can_reset,
                default_expanded=single_entry_category,
            )
            parent.sig_replace_parent.connect(self.sig_replace_parent)
            parent.sig_export_parent.connect(self.sig_export_parent)
            parent.sig_reset_parent.connect(self.sig_reset_parent)
            parent.sig_leaf_play.connect(self.sig_leaf_play)
            parent.sig_leaf_replace.connect(self.sig_leaf_replace)
            parent.sig_leaf_export.connect(self.sig_leaf_export)
            parent.sig_leaf_drop.connect(self.sig_leaf_drop)
            self._insert_widget(parent)

    def _build_fx_row(self, row: EntryRow) -> QFrame:
        icon = "🔊" if row.kind == EntryKind.OTHER_FX else "🚗"
        synthetic = EntryLeaf(kind=LeafKind.SAMPLE, name=row.name, icon=icon)

        widget = LeafRowWidget(synthetic, self._stylesheets)
        widget.sig_play.connect(lambda _leaf: self.sig_row_play.emit(row))
        widget.sig_replace.connect(lambda _leaf: self.sig_row_replace.emit(row))
        widget.sig_export.connect(lambda _leaf: self.sig_row_export.emit(row))
        widget.sig_drop.connect(lambda _leaf, path: self.sig_row_drop.emit(row, path))
        return widget

    def _insert_widget(self, widget: QWidget) -> None:
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, widget)

    def _clear_content(self) -> None:
        while self._scroll_layout.count() > 1:
            item = self._scroll_layout.takeAt(0)
            w = item.widget()

            if w is not None:
                w.deleteLater()
