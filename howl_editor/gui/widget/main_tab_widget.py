# coding: utf-8

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSplitter, QStackedWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from howl_editor.analysis.entry_leaves_builder import EntryLeavesBuilder
from howl_editor.analysis.semantic_entry_builder import SemanticEntryBuilder
from howl_editor.cseq.adventure_hub import AdventureHubMaskTable
from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.detail.leaf_info_formatter import LeafInfoFormatter
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.category_detail_widget import CategoryDetailWidget
from howl_editor.gui.widget.category_grid_widget import CategoryGridWidget
from howl_editor.gui.widget.player_widget import PlayerWidget
from howl_editor.gui.widget.waveform_widget import WaveformWidget
from howl_editor.howl.blob_snapshot import BlobSnapshot
from howl_editor.models import EntryGroup, EntryLeaf, HowlFile

_PAGE_EMPTY = 0
_PAGE_GRID = 1
_PAGE_DETAIL = 2


class MainTabWidget(QWidget):
    """Card-grid + drill-down navigation, with a right-side info / waveform /
    transport panel that only appears inside a category page. When the user
    backs out of a category while audio is still playing, the player widget
    relocates to a docked bar at the bottom of the tab so transport controls
    stay reachable.
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

    # (song_index, sub_song_index, active_tracks, label)
    sig_play_hub = Signal(int, int, object, str)

    def __init__(
        self,
        entry_builder: SemanticEntryBuilder,
        leaves_builder: EntryLeavesBuilder,
        snapshot: BlobSnapshot,
        stylesheet_loader: StylesheetLoader,
        hub_mask_table: AdventureHubMaskTable,
        icon_resolver: CategoryIconResolver,
        leaf_info_formatter: LeafInfoFormatter,
    ):
        super().__init__()
        self._builder = entry_builder
        self._leaves_builder = leaves_builder
        self._snapshot = snapshot
        self._stylesheets = stylesheet_loader
        self._hub_mask = hub_mask_table
        self._icon_resolver = icon_resolver
        self._leaf_info = leaf_info_formatter
        self._hwl: HowlFile | None = None
        self._groups: list[EntryGroup] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("mainTabRoot")
        self.setStyleSheet(self._stylesheets.load("main_tab.qss"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._build_left_panel())
        self._splitter.addWidget(self._build_right_panel())
        self._splitter.setSizes([720, 380])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        outer.addWidget(self._splitter, stretch=1)

        outer.addWidget(self._build_bottom_dock())

        # One shared player; we re-parent it between the sidebar slot and
        # the bottom dock slot as the user navigates / playback state changes.
        self.player_widget = PlayerWidget()
        self.player_widget.sig_active_changed.connect(self._on_player_active_changed)
        self._dock_player_to_sidebar()
        self._update_dock_visibility()

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

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
        self._detail.sig_leaf_selected.connect(self._on_leaf_selected)
        self._detail.sig_entry_selected.connect(self._on_entry_selected)
        self._detail.sig_row_play.connect(self.sig_row_play)
        self._detail.sig_row_replace.connect(self.sig_row_replace)
        self._detail.sig_row_export.connect(self.sig_row_export)
        self._detail.sig_row_drop.connect(self.sig_row_drop)
        self._detail.sig_play_hub.connect(self.sig_play_hub)
        self._stack.addWidget(self._detail)

        self._stack.currentChanged.connect(self._on_page_changed)
        self._stack.setCurrentIndex(_PAGE_EMPTY)

        return container

    def _build_right_panel(self) -> QWidget:
        self._sidebar = QFrame()
        self._sidebar.setObjectName("mainTabRightPanel")

        layout = QVBoxLayout(self._sidebar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setPlaceholderText("Select a sample or sequence to see its details.")
        layout.addWidget(self.info, stretch=1)

        self.waveform = WaveformWidget()
        self.waveform.setVisible(False)
        layout.addWidget(self.waveform)

        # Empty slot that the shared PlayerWidget gets parented into when the
        # sidebar is the active host (i.e. we're inside a category).
        self._sidebar_player_slot = QWidget()
        self._sidebar_player_layout = QVBoxLayout(self._sidebar_player_slot)
        self._sidebar_player_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._sidebar_player_slot)

        return self._sidebar

    def _build_bottom_dock(self) -> QWidget:
        """The fallback host for the player when the sidebar isn't visible.
        Stays hidden unless something is actually playing — otherwise an
        empty 'No audio' bar would just take up screen space."""
        self._bottom_dock = QFrame()
        self._bottom_dock.setObjectName("mainTabBottomDock")

        layout = QHBoxLayout(self._bottom_dock)
        layout.setContentsMargins(8, 4, 8, 4)
        self._bottom_dock_layout = layout

        self._bottom_dock.setVisible(False)
        return self._bottom_dock

    def _on_page_changed(self, _index: int) -> None:
        self._refresh_player_location()

    def _on_player_active_changed(self, _active: bool) -> None:
        self._refresh_player_location()

    def _refresh_player_location(self) -> None:
        # Called from QStackedWidget.currentChanged, which fires during the
        # initial setCurrentIndex before _build_ui is finished setting up
        # the player. Skip until everything is in place.
        if not hasattr(self, "player_widget"):
            self._sidebar.setVisible(self._stack.currentIndex() == _PAGE_DETAIL)
            return

        in_detail = self._stack.currentIndex() == _PAGE_DETAIL

        if in_detail:
            self._dock_player_to_sidebar()
        else:
            self._dock_player_to_bottom()

        self._sidebar.setVisible(in_detail)
        self._update_dock_visibility()

    def _dock_player_to_sidebar(self) -> None:
        if self.player_widget.parentWidget() is not self._sidebar_player_slot:
            self._sidebar_player_layout.addWidget(self.player_widget)

    def _dock_player_to_bottom(self) -> None:
        if self.player_widget.parentWidget() is not self._bottom_dock:
            self._bottom_dock_layout.addWidget(self.player_widget)

    def _update_dock_visibility(self) -> None:
        in_detail = self._stack.currentIndex() == _PAGE_DETAIL
        # The bottom dock only shows when (a) the sidebar isn't, and
        # (b) something is actively loaded in the player — otherwise we'd
        # surface an idle "No audio" bar on the grid for no reason.
        self._bottom_dock.setVisible(not in_detail and self.player_widget.is_active())

    def clear(self) -> None:
        self._hwl = None
        self._groups = []
        self._stack.setCurrentIndex(_PAGE_EMPTY)
        self._clear_info_panel()

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
        self._clear_info_panel()

    def _on_back(self) -> None:
        self._stack.setCurrentIndex(_PAGE_GRID)
        self._clear_info_panel()

    def _on_leaf_selected(self, leaf: EntryLeaf) -> None:
        self.info.setHtml(self._leaf_info.format(leaf, self._hwl))

    def _on_entry_selected(self, row, leaves) -> None:
        self.info.setHtml(self._leaf_info.format_entry(row, self._hwl, leaves))

    def _clear_info_panel(self) -> None:
        self.info.clear()
        self.waveform.clear()
        self.waveform.setVisible(False)
