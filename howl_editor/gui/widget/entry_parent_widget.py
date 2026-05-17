# coding: utf-8

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget,
)

from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget
from howl_editor.models import EntryLeaf, EntryRow, LeafKind


_KIND_ICON_FALLBACK = "•"
_ENTRY_ICON_PX = 32

# Tab indices inside the expanded panel. Samples is the default landing tab.
_TAB_SAMPLES = 0
_TAB_SEQUENCES = 1


class EntryParentWidget(QFrame):
    """An entry shown in the category detail view: name + status badges + the
    parent-level Replace/Export/Reset actions + a collapsible body containing
    a Samples / Sequences tab split of the entry's leaves.

    Default-expanded when there's more than one leaf, otherwise collapsed to
    keep dense categories scannable. No Play button at this level — playback
    only happens on leaves.
    """

    sig_replace_parent = Signal(object)         # EntryRow
    sig_export_parent = Signal(object)
    sig_reset_parent = Signal(object)
    sig_leaf_play = Signal(object)              # EntryLeaf
    sig_leaf_replace = Signal(object)
    sig_leaf_export = Signal(object)
    sig_leaf_drop = Signal(object, str)         # EntryLeaf, file_path

    def __init__(
        self,
        row: EntryRow,
        leaves: list[EntryLeaf],
        parent_icon: str,
        stylesheet_loader: StylesheetLoader,
        icon_resolver: CategoryIconResolver,
        can_reset: bool = False,
        default_expanded: bool = True,
        icon_image_path: Path | None = None,
    ):
        super().__init__()
        self._row = row
        self._leaves = leaves
        self._parent_icon = parent_icon
        self._stylesheets = stylesheet_loader
        self._icon_resolver = icon_resolver
        self._icon_image_path = icon_image_path
        self.setObjectName("entryParent")
        self._build_ui(can_reset, default_expanded)

    def _build_ui(self, can_reset: bool, default_expanded: bool) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)

        outer.addLayout(self._build_header(can_reset, default_expanded))

        self._body = self._build_body()
        outer.addWidget(self._body)
        self._body.setVisible(default_expanded and bool(self._leaves))

    def _build_body(self) -> QWidget:
        has_samples = any(leaf.kind == LeafKind.SAMPLE for leaf in self._leaves)
        has_sequences = any(leaf.kind == LeafKind.SEQUENCE for leaf in self._leaves)

        if has_samples and not has_sequences:
            return self._build_flat_body(LeafKind.SAMPLE)

        if has_sequences and not has_samples:
            return self._build_flat_body(LeafKind.SEQUENCE)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_leaf_tab(LeafKind.SAMPLE, "samples"), "Samples")
        tabs.addTab(self._build_leaf_tab(LeafKind.SEQUENCE, "sequences"), "Sequences")
        tabs.setCurrentIndex(_TAB_SAMPLES)
        tabs.currentChanged.connect(lambda idx: self._size_to_current_tab(tabs, idx))

        self._size_to_current_tab(tabs, _TAB_SAMPLES)

        return tabs

    def _build_flat_body(self, kind: LeafKind) -> QFrame:
        """Tabless body used when the entry has only one kind of leaf. Styled
        like the tab pane (palette(window) background + rounded border) so the
        visual container looks consistent whether tabs are shown or not."""
        container = QFrame()
        container.setObjectName("entryBodyContainer")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        for leaf in self._leaves:
            if leaf.kind != kind:
                continue

            leaf_icon = self._icon_resolver.resolve_leaf(leaf.name)
            row = LeafRowWidget(leaf, self._stylesheets, icon_image_path=leaf_icon)
            row.sig_play.connect(self.sig_leaf_play)
            row.sig_replace.connect(self.sig_leaf_replace)
            row.sig_export.connect(self.sig_leaf_export)
            row.sig_drop.connect(self.sig_leaf_drop)
            layout.addWidget(row)

        return container

    @staticmethod
    def _size_to_current_tab(tabs: QTabWidget, current_index: int) -> None:
        for i in range(tabs.count()):
            page = tabs.widget(i)
            policy = (
                QSizePolicy.Preferred if i == current_index else QSizePolicy.Ignored
            )
            page.setSizePolicy(QSizePolicy.Preferred, policy)

        tabs.updateGeometry()

    def _build_leaf_tab(self, kind: LeafKind, empty_label: str) -> QWidget:
        """Build one tab page containing leaf rows of the requested kind, or
        a soft empty-state label when the entry has none."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 6, 0, 4)
        layout.setSpacing(2)

        leaves = [leaf for leaf in self._leaves if leaf.kind == kind]

        if not leaves:
            empty = QLabel(f"No {empty_label} for this entry.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #8a8a8a; padding: 16px; font-size: 12px;")
            layout.addWidget(empty)
            layout.addStretch(1)
            return page

        for leaf in leaves:
            leaf_icon = self._icon_resolver.resolve_leaf(leaf.name)
            row = LeafRowWidget(leaf, self._stylesheets, icon_image_path=leaf_icon)
            row.sig_play.connect(self.sig_leaf_play)
            row.sig_replace.connect(self.sig_leaf_replace)
            row.sig_export.connect(self.sig_leaf_export)
            row.sig_drop.connect(self.sig_leaf_drop)
            layout.addWidget(row)

        layout.addStretch(1)

        return page

    def _build_header(self, can_reset: bool, default_expanded: bool) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(8)

        self._toggle_btn = QPushButton("▾" if default_expanded else "▸")
        self._toggle_btn.setObjectName("parentToggle")
        self._toggle_btn.setFixedWidth(26)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(default_expanded)
        self._toggle_btn.setToolTip("Show / hide this entry's sequences and samples")
        self._toggle_btn.toggled.connect(self._on_toggle)

        # No leaves to expand → hide the toggle entirely.
        if not self._leaves:
            self._toggle_btn.setVisible(False)

        header.addWidget(self._toggle_btn)

        header.addWidget(self._build_icon_label())

        name = QLabel(self._row.name)
        name.setObjectName("entryParentName")
        header.addWidget(name, stretch=1)

        if self._leaves:
            leaf_count = QLabel(
                f"{len(self._leaves)} item{'s' if len(self._leaves) != 1 else ''}"
            )
            leaf_count.setObjectName("leafDetail")
            header.addWidget(leaf_count)

        for badge in self._build_badges():
            header.addWidget(badge)

        if self._row.accepts:
            replace_btn = QPushButton("🔄  Replace")
            replace_btn.setFixedWidth(126)
            replace_btn.setToolTip("Replace the entire song or bank with a file")
            replace_btn.clicked.connect(lambda: self.sig_replace_parent.emit(self._row))
            header.addWidget(replace_btn)

        export_btn = QPushButton("💾  Export")
        export_btn.setFixedWidth(118)
        export_btn.setToolTip("Export the entire song or bank")
        export_btn.clicked.connect(lambda: self.sig_export_parent.emit(self._row))
        header.addWidget(export_btn)

        if can_reset and self._row.is_modified:
            reset_btn = QPushButton("↩️  Reset")
            reset_btn.setObjectName("parentReset")
            reset_btn.setFixedWidth(74)
            reset_btn.setToolTip("Restore the originally-loaded content for this slot")
            reset_btn.clicked.connect(lambda: self.sig_reset_parent.emit(self._row))
            header.addWidget(reset_btn)

        return header

    def _build_icon_label(self) -> QLabel:
        """Prefer a custom per-entry image if registered; otherwise fall back
        to the category-level emoji icon."""
        label = QLabel()
        label.setObjectName("entryParentIcon")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(_ENTRY_ICON_PX + 4)

        if self._icon_image_path is not None:
            pixmap = QPixmap(str(self._icon_image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    _ENTRY_ICON_PX, _ENTRY_ICON_PX,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                label.setPixmap(scaled)
                return label

        label.setText(self._parent_icon or _KIND_ICON_FALLBACK)
        return label

    def _on_toggle(self, checked: bool) -> None:
        self._body.setVisible(checked and bool(self._leaves))
        self._toggle_btn.setText("▾" if checked else "▸")

    def _build_badges(self) -> list[QLabel]:
        badges: list[QLabel] = []

        if self._row.is_modified:
            badges.append(self._make_badge("Modified", "#ff9500"))

        if self._row.is_broken:
            badges.append(self._make_badge(f"⚠ Missing {self._row.missing_count}", "#ff3b30"))

        return badges

    @staticmethod
    def _make_badge(text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: white; background: {color}; "
            f"padding: 2px 8px; border-radius: 9px; font-size: 11px; font-weight: 600;"
        )

        return label
