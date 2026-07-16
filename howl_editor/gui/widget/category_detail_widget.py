# coding: utf-8

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from howl_editor.ctr.formats.cseq.adventure_hub_mask_table_query import AdventureHubMaskTableQuery
from howl_editor.ctr.formats.howl.blob_snapshot import BlobSnapshot
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.entries.entry_leaf import EntryLeaf, LeafKind
from howl_editor.gui.entries.entry_leaves_builder import EntryLeavesBuilder
from howl_editor.gui.entries.semantic_entry import EntryGroup
from howl_editor.gui.entries.semantic_entry import EntryKind, EntryRow
from howl_editor.gui.layout import ButtonWidth, IconSize
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.entry_parent_widget import EntryParentWidget
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget


class CategoryDetailWidget(QWidget):
    """The Main tab's per-category page: back button + entries with leaves.

    For the Adventure Hub entry the parent widget exposes a hub dropdown +
    Play hub button; this widget catches the resulting `sig_play_hub` and
    resolves the chosen hub into the renderer's track-mask payload (sub-song
    index 0 + the list of tracks audible in that hub).
    """

    sig_back = Signal()
    sig_replace_parent = Signal(object)
    sig_export_song_parent = Signal(object)
    sig_export_bank_parent = Signal(object)
    sig_reset_parent = Signal(object)
    sig_remove_parent = Signal(object)
    sig_leaf_play = Signal(object)
    sig_leaf_replace = Signal(object)
    sig_leaf_copy = Signal(object)
    sig_leaf_export = Signal(object)
    sig_leaf_remove = Signal(object)
    sig_leaf_drop = Signal(object, str)
    sig_leaf_selected = Signal(object)        # user clicked a leaf row
    sig_entry_selected = Signal(object, object)   # row + its leaves
    sig_row_play = Signal(object)             # for FX entries that ARE leaves
    sig_row_replace = Signal(object)
    sig_row_drop = Signal(object, str)
    sig_play_hub = Signal(int, int, object, str)

    def __init__(
        self,
        leaves_builder: EntryLeavesBuilder,
        snapshot: BlobSnapshot,
        stylesheet_loader: StylesheetLoader,
        hub_mask_table_query: AdventureHubMaskTableQuery,
        icon_resolver: CategoryIconResolver,
        badge_resolver=None,
    ):
        super().__init__()
        self._leaves_builder = leaves_builder
        self._snapshot = snapshot
        self._stylesheets = stylesheet_loader
        self._hub_mask_table_query = hub_mask_table_query
        self._icon_resolver = icon_resolver
        self._badge_resolver = badge_resolver
        self._current_group: EntryGroup | None = None
        self._current_hwl: HowlFile | None = None
        self._diag_index = None
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

        back = QPushButton("⬅️  Categories")
        back.setObjectName("backButton")
        back.setFixedWidth(ButtonWidth.BACK)
        back.clicked.connect(self.sig_back)
        layout.addWidget(back)

        self._title_icon = QLabel()
        self._title_icon.setObjectName("detailIcon")
        layout.addWidget(self._title_icon)

        self._title = QLabel()
        self._title.setObjectName("detailTitle")
        layout.addWidget(self._title, stretch=1)

        return header

    def show_category(self, hwl: HowlFile, group: EntryGroup, diag_index=None) -> None:
        self._current_hwl = hwl
        self._current_group = group
        self._diag_index = diag_index
        self._title.setText(group.name)
        self._update_title_icon(group)
        self._render_entries()

    def _update_title_icon(self, group: EntryGroup) -> None:
        image_path = self._icon_resolver.resolve(group.name)

        if image_path is not None:
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    IconSize.CATEGORY_TITLE, IconSize.CATEGORY_TITLE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self._title_icon.setPixmap(scaled)
                self._title_icon.setFixedHeight(IconSize.CATEGORY_TITLE)
                return

        self._title_icon.clear()
        self._title_icon.setText(group.icon)

    def _on_play_hub(self, row: EntryRow, hub_index: int) -> None:
        """Resolve a Play-hub request into the renderer's expected payload:
        the song slot, the sub-song that holds the main hub music (index 0),
        the list of track indices unmuted for the chosen hub, and a label."""
        if row.song_index is None:
            return

        active_tracks = self._hub_mask_table_query.tracks_for_hub(hub_index)
        label = f"Adventure Hub · {self._hub_mask_table_query.hub_name(hub_index)}"
        self.sig_play_hub.emit(row.song_index, 0, active_tracks, label)

    def _render_entries(self) -> None:
        if self._current_hwl is None or self._current_group is None:
            return

        self._clear_content()
        can_reset = self._snapshot.has_snapshot()
        single_entry_category = len(self._current_group.rows) <= 1

        for row in self._current_group.rows:
            if row.kind in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX):
                self._insert_widget(self._build_fx_row(row))
                continue

            leaves = self._leaves_builder.build(self._current_hwl, row)

            entry_icon = self._icon_resolver.resolve_entry(
                row.name, self._current_group.name,
            )

            hub_names: tuple[str, ...] = ()
            if row.kind == EntryKind.ADVENTURE_HUB:
                hub_names = self._hub_mask_table_query.hub_names()

            parent = EntryParentWidget(
                row, leaves, self._current_group.icon, self._stylesheets,
                self._icon_resolver,
                can_reset=can_reset,
                default_expanded=single_entry_category,
                icon_image_path=entry_icon,
                hub_names=hub_names,
                diagnostic_badge=self._row_badge(row),
                diagnostic_label=self._row_label(row),
                diagnostic_tooltip=self._row_tooltip(row),
            )
            parent.sig_replace_parent.connect(self.sig_replace_parent)
            parent.sig_export_song_parent.connect(self.sig_export_song_parent)
            parent.sig_export_bank_parent.connect(self.sig_export_bank_parent)
            parent.sig_reset_parent.connect(self.sig_reset_parent)
            parent.sig_remove_parent.connect(self.sig_remove_parent)
            parent.sig_leaf_play.connect(self.sig_leaf_play)
            parent.sig_leaf_replace.connect(self.sig_leaf_replace)
            parent.sig_leaf_copy.connect(self.sig_leaf_copy)
            parent.sig_leaf_export.connect(self.sig_leaf_export)
            parent.sig_leaf_remove.connect(self.sig_leaf_remove)
            parent.sig_leaf_drop.connect(self.sig_leaf_drop)
            parent.sig_leaf_selected.connect(self.sig_leaf_selected)
            parent.sig_entry_selected.connect(self.sig_entry_selected)
            parent.sig_play_hub.connect(self._on_play_hub)
            self._insert_widget(parent)

    def _row_badge(self, row: EntryRow) -> str:
        if self._badge_resolver is None:
            return ""

        return self._badge_resolver.row_badge(self._diag_index, row)

    def _row_label(self, row: EntryRow) -> str:
        if self._badge_resolver is None:
            return ""

        return self._badge_resolver.row_label(self._diag_index, row)

    def _row_tooltip(self, row: EntryRow) -> str:
        if self._badge_resolver is None:
            return ""

        findings = self._badge_resolver.row_findings(self._diag_index, row)
        return "\n".join(f.message for f in findings)

    def _build_fx_row(self, row: EntryRow) -> QFrame:
        icon = "🔊" if row.kind == EntryKind.OTHER_FX else "🚗"
        synthetic = EntryLeaf(kind=LeafKind.SAMPLE, name=row.name, icon=icon)

        leaf_icon = self._icon_resolver.resolve_entry(
            row.name, self._current_group.name,
        ) if self._current_group else None

        widget = LeafRowWidget(
            synthetic,
            self._stylesheets,
            icon_image_path=leaf_icon,
            show_replace=False,
            show_export=False,
            show_remove=False,
        )

        widget.sig_play.connect(lambda _leaf: self.sig_row_play.emit(row))
        widget.sig_drop.connect(lambda _leaf, path: self.sig_row_drop.emit(row, path))
        widget.sig_selected.connect(lambda _leaf: self.sig_entry_selected.emit(row, []))
        return widget

    def _insert_widget(self, widget: QWidget) -> None:
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, widget)

    def _clear_content(self) -> None:
        while self._scroll_layout.count() > 1:
            item = self._scroll_layout.takeAt(0)
            w = item.widget()

            if w is not None:
                w.deleteLater()
