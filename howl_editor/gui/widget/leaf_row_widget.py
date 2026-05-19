# coding: utf-8

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton

from howl_editor.file_format_registry import FileFormatRegistry
from howl_editor.gui.entries.entry_leaf import EntryLeaf, LeafKind
from howl_editor.gui.layout import ButtonWidth, IconSize
from howl_editor.gui.stylesheet_loader import StylesheetLoader

_LEAF_ACCEPTS = {
    LeafKind.SEQUENCE: (FileFormatRegistry.CSEQ.extension, FileFormatRegistry.MIDI.extension),
    LeafKind.SAMPLE: (FileFormatRegistry.VAG.extension, FileFormatRegistry.WAV.extension),
}


class LeafRowWidget(QFrame):
    """One playable leaf (sequence or sample). Play is a dedicated button;
    Replace / Export / Remove are grouped under a single Actions menu so the
    row stays scannable as more actions get added."""

    sig_play = Signal(object)        # EntryLeaf
    sig_replace = Signal(object)
    sig_copy = Signal(object)
    sig_export = Signal(object)
    sig_remove = Signal(object)
    sig_drop = Signal(object, str)   # EntryLeaf, file_path
    sig_selected = Signal(object)    # EntryLeaf — emitted on row click (not button click)

    def __init__(
        self,
        leaf: EntryLeaf,
        stylesheet_loader: StylesheetLoader,
        icon_image_path: Path | None = None,
        show_play: bool = True,
        show_replace: bool = True,
        show_copy: bool | None = None,
        show_export: bool = True,
        show_remove: bool = True,
    ):
        super().__init__()
        self._leaf = leaf
        self._icon_image_path = icon_image_path
        self._show_play = show_play
        self._show_replace = show_replace
        # Copy is supported for both samples (→ another bank) and sequences
        # (→ another song). Caller can still force it off via show_copy=False.
        self._show_copy = True if show_copy is None else show_copy
        self._show_export = show_export
        self._show_remove = show_remove
        self.setObjectName("leafRow")
        # Stylesheet is set by the parent panel (category_detail.qss covers all leaves)
        # so we don't double-apply it here.
        self.setAcceptDrops(True)
        self._build_ui()

    @property
    def leaf(self) -> EntryLeaf:
        return self._leaf

    @property
    def accepts(self) -> tuple[str, ...]:
        return _LEAF_ACCEPTS.get(self._leaf.kind, ())

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        layout.addWidget(self._build_icon_label())

        name = QLabel(self._leaf.name)
        name.setObjectName("leafName")
        layout.addWidget(name, stretch=1)

        detail = QLabel(self._format_detail())
        detail.setObjectName("leafDetail")
        layout.addWidget(detail)

        if self._show_play:
            play_btn = QPushButton("▶️")
            play_btn.setObjectName("leafPlay")
            play_btn.setToolTip("Play")
            play_btn.setFixedWidth(ButtonWidth.LEAF_PLAY)
            play_btn.clicked.connect(lambda: self.sig_play.emit(self._leaf))
            layout.addWidget(play_btn)

        actions_btn = self._build_actions_button()
        if actions_btn is not None:
            layout.addWidget(actions_btn)

    def _build_actions_button(self) -> QPushButton | None:
        """Build the single Actions ▾ menu button. Returns None when the leaf
        has nothing to offer — so the row collapses to just Play (or even
        nothing)."""
        menu = QMenu(self)

        if self._show_replace:
            menu.addAction("🔄  Replace", lambda: self.sig_replace.emit(self._leaf))

        if self._show_copy:
            copy_label = (
                "📋  Copy to song…" if self._leaf.kind == LeafKind.SEQUENCE
                else "📋  Copy to bank…"
            )
            menu.addAction(copy_label, lambda: self.sig_copy.emit(self._leaf))

        if self._show_export:
            menu.addAction("💾  Export", lambda: self.sig_export.emit(self._leaf))

        if self._show_remove:
            if not menu.isEmpty():
                menu.addSeparator()
            
            menu.addAction("🗑️  Remove", lambda: self.sig_remove.emit(self._leaf))

        if menu.isEmpty():
            return None

        button = QPushButton("⚙️")
        button.setObjectName("leafActions")
        button.setToolTip("Actions")
        button.setFixedWidth(ButtonWidth.LEAF_ACTIONS)
        button.setMenu(menu)
        return button

    def _build_icon_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("leafIcon")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(IconSize.LEAF + 2)

        if self._icon_image_path is not None:
            pixmap = QPixmap(str(self._icon_image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    IconSize.LEAF, IconSize.LEAF,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                label.setPixmap(scaled)
                return label

        label.setText(self._leaf.icon)
        return label

    def _format_detail(self) -> str:
        if self._leaf.kind == LeafKind.SEQUENCE and self._leaf.seq_index is not None:
            return f"Seq #{self._leaf.seq_index}"

        if self._leaf.kind == LeafKind.SAMPLE and self._leaf.spu_index is not None:
            return f"SPU #{self._leaf.spu_index}"

        return ""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click anywhere on the row body (not the buttons; their child
        widgets consume the event first) selects this leaf so the right-side
        info panel can show its details.

        We `accept()` the event so it doesn't bubble up to the enclosing
        EntryParentWidget — otherwise its own selection handler would fire
        right after and overwrite the leaf details with the parent row's."""
        if event.button() == Qt.LeftButton:
            self.sig_selected.emit(self._leaf)
            event.accept()
            return

        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not event.mimeData().hasUrls():
            return

        for url in event.mimeData().urls():
            ext = Path(url.toLocalFile()).suffix.lower()
            if ext in self.accepts:
                event.acceptProposedAction()
                return

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = Path(path).suffix.lower()

            if ext in self.accepts:
                self.sig_drop.emit(self._leaf, path)
                event.acceptProposedAction()
                return
