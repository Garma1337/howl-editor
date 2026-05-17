# coding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget
from howl_editor.models import EntryLeaf, EntryRow


_KIND_ICON_FALLBACK = "•"


class EntryParentWidget(QFrame):
    """An entry shown in the category detail view: name + status badges + the
    parent-level Replace/Export/Reset actions + a collapsible list of leaf rows
    underneath. Default-expanded when there's more than one leaf, otherwise
    collapsed to keep dense categories scannable.

    No Play button at this level — playback only happens on leaves.
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
        can_reset: bool = False,
        default_expanded: bool = True,
    ):
        super().__init__()
        self._row = row
        self._leaves = leaves
        self._parent_icon = parent_icon
        self._stylesheets = stylesheet_loader
        self.setObjectName("entryParent")
        self._build_ui(can_reset, default_expanded)

    def _build_ui(self, can_reset: bool, default_expanded: bool) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)

        outer.addLayout(self._build_header(can_reset, default_expanded))

        self._leaves_container = QWidget()
        leaves_layout = QVBoxLayout(self._leaves_container)
        leaves_layout.setContentsMargins(0, 0, 0, 0)
        leaves_layout.setSpacing(2)

        for leaf in self._leaves:
            row = LeafRowWidget(leaf, self._stylesheets)
            row.sig_play.connect(self.sig_leaf_play)
            row.sig_replace.connect(self.sig_leaf_replace)
            row.sig_export.connect(self.sig_leaf_export)
            row.sig_drop.connect(self.sig_leaf_drop)
            leaves_layout.addWidget(row)

        outer.addWidget(self._leaves_container)
        self._leaves_container.setVisible(default_expanded and bool(self._leaves))

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

        icon = QLabel(self._parent_icon or _KIND_ICON_FALLBACK)
        icon.setObjectName("entryParentIcon")
        icon.setFixedWidth(28)
        header.addWidget(icon)

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
            replace_btn = QPushButton("↻  Replace whole")
            replace_btn.setFixedWidth(126)
            replace_btn.setToolTip("Replace the entire song or bank with a file")
            replace_btn.clicked.connect(lambda: self.sig_replace_parent.emit(self._row))
            header.addWidget(replace_btn)

        export_btn = QPushButton("⤓  Export whole")
        export_btn.setFixedWidth(118)
        export_btn.setToolTip("Export the entire song or bank")
        export_btn.clicked.connect(lambda: self.sig_export_parent.emit(self._row))
        header.addWidget(export_btn)

        if can_reset and self._row.is_modified:
            reset_btn = QPushButton("↺  Reset")
            reset_btn.setObjectName("parentReset")
            reset_btn.setFixedWidth(74)
            reset_btn.setToolTip("Restore the originally-loaded content for this slot")
            reset_btn.clicked.connect(lambda: self.sig_reset_parent.emit(self._row))
            header.addWidget(reset_btn)

        return header

    def _on_toggle(self, checked: bool) -> None:
        self._leaves_container.setVisible(checked and bool(self._leaves))
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
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: white; background: {color}; "
            f"padding: 2px 8px; border-radius: 9px; font-size: 11px; font-weight: 600;"
        )
        return lbl
