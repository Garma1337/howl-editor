# coding: utf-8

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.models import EntryLeaf, LeafKind

_LEAF_ACCEPTS = {
    LeafKind.SEQUENCE: (".cseq", ".mid"),
    LeafKind.SAMPLE: (".vag", ".wav"),
}

_LEAF_ICON_PX = 22


class LeafRowWidget(QFrame):
    """One playable leaf (sequence or sample) — the only place Play exists."""

    sig_play = Signal(object)        # EntryLeaf
    sig_replace = Signal(object)
    sig_export = Signal(object)
    sig_drop = Signal(object, str)   # EntryLeaf, file_path

    def __init__(
        self,
        leaf: EntryLeaf,
        stylesheet_loader: StylesheetLoader,
        icon_image_path: Path | None = None,
    ):
        super().__init__()
        self._leaf = leaf
        self._icon_image_path = icon_image_path
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

        play_btn = QPushButton("▶️  Play")
        play_btn.setObjectName("leafPlay")
        play_btn.setFixedWidth(64)
        play_btn.clicked.connect(lambda: self.sig_play.emit(self._leaf))
        layout.addWidget(play_btn)

        replace_btn = QPushButton("🔄  Replace")
        replace_btn.setFixedWidth(82)
        replace_btn.clicked.connect(lambda: self.sig_replace.emit(self._leaf))
        layout.addWidget(replace_btn)

        export_btn = QPushButton("💾  Export")
        export_btn.setFixedWidth(78)
        export_btn.clicked.connect(lambda: self.sig_export.emit(self._leaf))
        layout.addWidget(export_btn)

    def _build_icon_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("leafIcon")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(_LEAF_ICON_PX + 2)

        if self._icon_image_path is not None:
            pixmap = QPixmap(str(self._icon_image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    _LEAF_ICON_PX, _LEAF_ICON_PX,
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
