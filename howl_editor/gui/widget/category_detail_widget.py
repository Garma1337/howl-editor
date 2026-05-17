# coding: utf-8

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from howl_editor.analysis.entry_leaves import EntryLeavesBuilder
from howl_editor.cseq.adventure_hub import AdventureHubMaskTable
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.entry_parent_widget import EntryParentWidget
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget
from howl_editor.howl.blob_snapshot import BlobSnapshot
from howl_editor.models import EntryGroup, EntryLeaf, HowlFile, LeafKind
from howl_editor.models.semantic_entry import EntryKind, EntryRow

_HUB_ALL = -1
_TITLE_ICON_PX = 40


class CategoryDetailWidget(QWidget):
    """The Main tab's per-category page: back button + entries with leaves.

    The Adventure Hub category gets an extra hub selector — picking a hub
    filters the visible sequences to the ones that hub actually hears at
    runtime (via the hub-bitmask table). Bank samples are always shown.
    """

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
    sig_play_hub_preview = Signal(int, object, str)

    def __init__(
        self,
        leaves_builder: EntryLeavesBuilder,
        snapshot: BlobSnapshot,
        stylesheet_loader: StylesheetLoader,
        hub_mask_table: AdventureHubMaskTable,
        icon_resolver: CategoryIconResolver,
    ):
        super().__init__()
        self._leaves_builder = leaves_builder
        self._snapshot = snapshot
        self._stylesheets = stylesheet_loader
        self._hub_mask = hub_mask_table
        self._icon_resolver = icon_resolver
        self._current_group: EntryGroup | None = None
        self._current_hwl: HowlFile | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(self._stylesheets.load("category_detail.qss"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = self._build_header()
        outer.addWidget(self._header)

        self._hub_filter_bar = self._build_hub_filter_bar()
        self._hub_filter_bar.setVisible(False)
        outer.addWidget(self._hub_filter_bar)

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

    def _build_hub_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("categoryDetailHeader")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 8)
        layout.setSpacing(8)

        label = QLabel("Preview as:")
        label.setObjectName("detailTitle")
        label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(label)

        self._hub_combo = QComboBox()
        self._hub_combo.addItem("🌍  All sequences", _HUB_ALL)

        for hub_idx in range(self._hub_mask.num_hubs):
            self._hub_combo.addItem(self._hub_mask.hub_name(hub_idx), hub_idx)

        self._hub_combo.currentIndexChanged.connect(self._on_hub_changed)
        layout.addWidget(self._hub_combo)

        play_preview_btn = QPushButton("▶️  Play preview")
        play_preview_btn.setObjectName("backButton")
        play_preview_btn.setFixedWidth(140)
        play_preview_btn.setToolTip("Render this hub's audible sequences mixed together")
        play_preview_btn.clicked.connect(self._on_play_hub_preview)
        layout.addWidget(play_preview_btn)

        layout.addStretch(1)
        return bar

    def show_category(self, hwl: HowlFile, group: EntryGroup) -> None:
        self._current_hwl = hwl
        self._current_group = group
        self._title.setText(group.name)
        self._update_title_icon(group)

        is_hub_category = any(r.kind == EntryKind.ADVENTURE_HUB for r in group.rows)
        self._hub_filter_bar.setVisible(is_hub_category)

        if is_hub_category:
            self._hub_combo.blockSignals(True)
            self._hub_combo.setCurrentIndex(0)
            self._hub_combo.blockSignals(False)

        self._render_entries()

    def _update_title_icon(self, group: EntryGroup) -> None:
        image_path = self._icon_resolver.resolve(group.name)

        if image_path is not None:
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    _TITLE_ICON_PX, _TITLE_ICON_PX,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self._title_icon.setPixmap(scaled)
                self._title_icon.setFixedHeight(_TITLE_ICON_PX)
                return

        self._title_icon.clear()
        self._title_icon.setText(group.icon)

    def _on_hub_changed(self) -> None:
        self._render_entries()

    def _on_play_hub_preview(self) -> None:
        if self._current_group is None:
            return

        hub_row = next(
            (r for r in self._current_group.rows if r.kind == EntryKind.ADVENTURE_HUB),
            None,
        )

        if hub_row is None or hub_row.song_index is None:
            return

        hub_index = self._hub_combo.currentData()

        if hub_index == _HUB_ALL:
            seq_indices = list(range(self._hub_mask.num_sequences))
            label = "Adventure Hub · all sequences"
        else:
            seq_indices = self._hub_mask.sequences_for_hub(hub_index)
            label = f"Adventure Hub · {self._hub_mask.hub_name(hub_index)}"

        self.sig_play_hub_preview.emit(hub_row.song_index, seq_indices, label)

    def _render_entries(self) -> None:
        if self._current_hwl is None or self._current_group is None:
            return

        self._clear_content()
        can_reset = self._snapshot.has_snapshot()
        single_entry_category = len(self._current_group.rows) <= 1
        hub_filter = self._selected_hub_filter()

        for row in self._current_group.rows:
            if row.kind in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX):
                self._insert_widget(self._build_fx_row(row))
                continue

            leaves = self._leaves_builder.build(self._current_hwl, row)

            if row.kind == EntryKind.ADVENTURE_HUB and hub_filter is not None:
                leaves = self._filter_for_hub(leaves, hub_filter)

            entry_icon = self._icon_resolver.resolve_entry(
                row.name, self._current_group.name,
            )

            parent = EntryParentWidget(
                row, leaves, self._current_group.icon, self._stylesheets,
                self._icon_resolver,
                can_reset=can_reset,
                default_expanded=single_entry_category,
                icon_image_path=entry_icon,
            )
            parent.sig_replace_parent.connect(self.sig_replace_parent)
            parent.sig_export_parent.connect(self.sig_export_parent)
            parent.sig_reset_parent.connect(self.sig_reset_parent)
            parent.sig_leaf_play.connect(self.sig_leaf_play)
            parent.sig_leaf_replace.connect(self.sig_leaf_replace)
            parent.sig_leaf_export.connect(self.sig_leaf_export)
            parent.sig_leaf_drop.connect(self.sig_leaf_drop)
            self._insert_widget(parent)

    def _selected_hub_filter(self) -> int | None:
        if not self._hub_filter_bar.isVisible():
            return None

        hub_index = self._hub_combo.currentData()
        return None if hub_index == _HUB_ALL else hub_index

    def _filter_for_hub(self, leaves: list[EntryLeaf], hub_index: int) -> list[EntryLeaf]:
        active = set(self._hub_mask.sequences_for_hub(hub_index))

        return [
            leaf for leaf in leaves
            if leaf.kind != LeafKind.SEQUENCE or leaf.seq_index in active
        ]

    def _build_fx_row(self, row: EntryRow) -> QFrame:
        icon = "🔊" if row.kind == EntryKind.OTHER_FX else "🚗"
        synthetic = EntryLeaf(kind=LeafKind.SAMPLE, name=row.name, icon=icon)

        leaf_icon = self._icon_resolver.resolve_entry(
            row.name, self._current_group.name,
        ) if self._current_group else None

        widget = LeafRowWidget(synthetic, self._stylesheets, icon_image_path=leaf_icon)
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
