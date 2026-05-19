# coding: utf-8

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy,
    QTabWidget, QVBoxLayout, QWidget,
)

from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.entries.entry_leaf import EntryLeaf, LeafKind
from howl_editor.gui.entries.semantic_entry import EntryKind
from howl_editor.gui.entries.semantic_entry import EntryRow
from howl_editor.gui.layout import ButtonWidth, IconSize, Inset
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.leaf_row_widget import LeafRowWidget

_KIND_ICON_FALLBACK = "•"

_TAB_SAMPLES = 0
_TAB_SEQUENCES = 1


class EntryParentWidget(QFrame):
    """An entry shown in the category detail view: name + status badges + a
    single Actions menu (Replace / Export / Reset / Remove, as applicable) +
    a collapsible body containing a Samples / Sequences tab split of the
    entry's leaves.

    Default-expanded when there's more than one leaf, otherwise collapsed to
    keep dense categories scannable. No Play button at this level — playback
    only happens on leaves.
    """

    sig_replace_parent = Signal(object)         # EntryRow
    sig_export_song_parent = Signal(object)
    sig_export_bank_parent = Signal(object)
    sig_reset_parent = Signal(object)
    sig_remove_parent = Signal(object)
    # Adventure Hub: emits (row, hub_index) when the user clicks Play hub
    # after picking a hub world from the inline dropdown.
    sig_play_hub = Signal(object, int)
    sig_leaf_play = Signal(object)              # EntryLeaf
    sig_leaf_replace = Signal(object)
    sig_leaf_export = Signal(object)
    sig_leaf_remove = Signal(object)
    sig_leaf_drop = Signal(object, str)         # EntryLeaf, file_path
    sig_leaf_selected = Signal(object)          # EntryLeaf — user clicked the row
    # EntryRow + the entry's leaves — sidebar uses the leaf count + breakdown
    # so the header no longer needs to surface it inline.
    sig_entry_selected = Signal(object, object)

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
        hub_names: tuple[str, ...] | list[str] = (),
    ):
        super().__init__()
        self._row = row
        self._leaves = leaves
        self._parent_icon = parent_icon
        self._stylesheets = stylesheet_loader
        self._icon_resolver = icon_resolver
        self._icon_image_path = icon_image_path
        self._hub_names = tuple(hub_names)
        self._hub_combo: QComboBox | None = None
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
        layout.setContentsMargins(Inset.BODY, Inset.BODY, Inset.BODY, Inset.BODY)
        layout.setSpacing(2)

        for leaf in self._leaves:
            if leaf.kind != kind:
                continue

            leaf_icon = self._icon_resolver.resolve_leaf(leaf.name)
            row = LeafRowWidget(
                leaf, self._stylesheets, icon_image_path=leaf_icon,
                show_play=self._leaf_supports_solo_play(leaf),
            )
            row.sig_play.connect(self.sig_leaf_play)
            row.sig_replace.connect(self.sig_leaf_replace)
            row.sig_export.connect(self.sig_leaf_export)
            row.sig_remove.connect(self.sig_leaf_remove)
            row.sig_drop.connect(self.sig_leaf_drop)
            row.sig_selected.connect(self.sig_leaf_selected)
            layout.addWidget(row)

        return container

    def _leaf_supports_solo_play(self, leaf: EntryLeaf) -> bool:
        return True

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click anywhere on the entry header (outside buttons / combo) fires
        entry selection. Child widgets like QPushButton consume the event
        first via Qt's normal propagation, so the bare label / icon / row
        background still selects without hijacking action clicks."""
        if event.button() == Qt.LeftButton:
            self.sig_entry_selected.emit(self._row, self._leaves)

        super().mousePressEvent(event)

    def _resolve_hub_icon(self, hub_name: str) -> QIcon | None:
        """Look up a per-hub portrait under `images/adventure_hub/<slug>.png`
        and return it as a QIcon. Falls back to None when no file exists, so
        the caller can use a text label instead."""
        if self._icon_resolver is None:
            return None

        path = self._icon_resolver.resolve_entry(hub_name, "Adventure Hub")
        if path is None:
            return None

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None

        return QIcon(pixmap)

    def _on_play_hub_clicked(self) -> None:
        if self._hub_combo is None:
            return

        hub_index = self._hub_combo.currentData()
        if hub_index is None:
            return

        self.sig_play_hub.emit(self._row, int(hub_index))

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
        page.setObjectName("entryTabPage")
        page.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(Inset.BODY, Inset.BODY, Inset.BODY, Inset.BODY)
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
            row = LeafRowWidget(
                leaf, self._stylesheets, icon_image_path=leaf_icon,
                show_play=self._leaf_supports_solo_play(leaf),
            )
            row.sig_play.connect(self.sig_leaf_play)
            row.sig_replace.connect(self.sig_leaf_replace)
            row.sig_export.connect(self.sig_leaf_export)
            row.sig_remove.connect(self.sig_leaf_remove)
            row.sig_drop.connect(self.sig_leaf_drop)
            row.sig_selected.connect(self.sig_leaf_selected)
            layout.addWidget(row)

        layout.addStretch(1)

        return page

    def _build_header(self, can_reset: bool, default_expanded: bool) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(8)

        self._toggle_btn = QPushButton("▾" if default_expanded else "▸")
        self._toggle_btn.setObjectName("parentToggle")
        self._toggle_btn.setFixedWidth(ButtonWidth.ENTRY_TOGGLE)
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

        for badge in self._build_badges():
            header.addWidget(badge)

        is_adventure_hub = self._row.kind == EntryKind.ADVENTURE_HUB

        if is_adventure_hub and self._hub_names:
            self._hub_combo = QComboBox()
            self._hub_combo.setToolTip(
                "Pick which Adventure Hub world's mix to hear when you click "
                "▶️ Play hub. Different hubs unmute different tracks of the "
                "shared main-music sub-song.",
            )
            self._hub_combo.setIconSize(QSize(IconSize.LEAF, IconSize.LEAF))

            for hub_idx, hub_name in enumerate(self._hub_names):
                icon = self._resolve_hub_icon(hub_name)
                if icon is not None:
                    self._hub_combo.addItem(icon, hub_name, hub_idx)
                else:
                    self._hub_combo.addItem(f"🌍  {hub_name}", hub_idx)

            header.addWidget(self._hub_combo)

            play_hub_btn = QPushButton("▶️  Play hub")
            play_hub_btn.setFixedWidth(ButtonWidth.HUB_PLAY)
            play_hub_btn.setToolTip(
                "Play the Adventure Hub main music with only the tracks the "
                "selected hub plays in-game. Each hub unmutes a different "
                "combination of tracks via the runtime hub-tracks mask.",
            )
            play_hub_btn.clicked.connect(self._on_play_hub_clicked)
            header.addWidget(play_hub_btn)

        actions_btn = self._build_actions_button(can_reset)
        if actions_btn is not None:
            header.addWidget(actions_btn)

        return header

    def _build_actions_button(self, can_reset: bool) -> QPushButton | None:
        """Single Actions ▾ menu collecting Replace / Export / Reset / Remove
        for this entry. Returns None when the entry has nothing actionable —
        FX entries fall into that bucket since they're effectively leaves and
        their own LeafRowWidget owns their actions."""
        menu = QMenu(self)

        if self._row.accepts:
            menu.addAction("🔄  Replace", lambda: self.sig_replace_parent.emit(self._row))

        if self._row.song_index is not None and self._can_export():
            menu.addAction("💾  Export song", lambda: self.sig_export_song_parent.emit(self._row))

        if self._row.bank_index is not None and self._can_export():
            menu.addAction("💾  Export bank", lambda: self.sig_export_bank_parent.emit(self._row))

        if can_reset and self._row.is_modified:
            menu.addAction("↩️  Reset", lambda: self.sig_reset_parent.emit(self._row))

        if self._can_remove():
            if not menu.isEmpty():
                menu.addSeparator()
            menu.addAction("🗑️  Remove", lambda: self.sig_remove_parent.emit(self._row))

        if menu.isEmpty():
            return None

        button = QPushButton("⚙️")
        button.setObjectName("parentActions")
        button.setToolTip("Actions")
        button.setFixedWidth(ButtonWidth.ENTRY_ACTIONS)
        button.setMenu(menu)
        return button

    def _can_export(self) -> bool:
        # FX entries ARE leaves; they have no separate file to export. Every
        # other entry kind can export at least one of its halves.
        return self._row.kind not in (EntryKind.OTHER_FX, EntryKind.ENGINE_FX)

    def _can_remove(self) -> bool:
        """Pure-song entries are removable from the category view; the
        file-content view still owns destructive bank / track operations."""
        return self._row.kind in (EntryKind.SHARED_SONG, EntryKind.CUSTOM_SONG)

    def _build_icon_label(self) -> QLabel:
        """Prefer a custom per-entry image if registered; otherwise fall back
        to the category-level emoji icon."""
        label = QLabel()
        label.setObjectName("entryParentIcon")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(IconSize.ENTRY + 4)

        if self._icon_image_path is not None:
            pixmap = QPixmap(str(self._icon_image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    IconSize.ENTRY, IconSize.ENTRY,
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
            badges.append(self._make_badge(f"⚠️ Missing {self._row.missing_count}", "#ff3b30"))

        return badges

    @staticmethod
    def _make_badge(text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: white; background: {color}; "
            f"padding: 2px 8px; border-radius: 9px; font-size: 11px; font-weight: 600;"
        )

        return label
