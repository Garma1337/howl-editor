# coding: utf-8

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.models import EntryGroup


class CategoryCardWidget(QFrame):
    """A big tappable category card shown on the Main tab grid.

    Click → emits sig_clicked with the underlying EntryGroup so the host can
    swap to the category's detail view.
    """

    sig_clicked = Signal(object)  # EntryGroup

    def __init__(
        self,
        group: EntryGroup,
        modified_count: int,
        stylesheet_loader: StylesheetLoader,
    ):
        super().__init__()
        self._group = group
        self._modified_count = modified_count
        self.setObjectName("categoryCard")
        self.setStyleSheet(stylesheet_loader.load("category_card.qss"))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(200, 140)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 12)
        outer.setSpacing(6)

        icon = QLabel(self._group.icon)
        icon.setObjectName("categoryIcon")
        icon.setAlignment(Qt.AlignCenter)
        outer.addWidget(icon)

        name = QLabel(self._group.name)
        name.setObjectName("categoryName")
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        outer.addWidget(name)

        outer.addStretch(1)

        chips = QHBoxLayout()
        chips.setSpacing(6)
        chips.addStretch(1)

        count = QLabel(f"{len(self._group.rows)}")
        count.setObjectName("categoryCount")
        chips.addWidget(count)

        if self._modified_count > 0:
            modified = QLabel(f"{self._modified_count} modified")
            modified.setObjectName("categoryModified")
            chips.addWidget(modified)

        chips.addStretch(1)
        outer.addLayout(chips)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.sig_clicked.emit(self._group)

        super().mousePressEvent(event)
