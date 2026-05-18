# coding: utf-8

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from howl_editor.gui.category_icon_resolver import CategoryIconResolver
from howl_editor.gui.entries.semantic_entry import EntryGroup
from howl_editor.gui.layout import IconSize
from howl_editor.gui.stylesheet_loader import StylesheetLoader


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
        icon_resolver: CategoryIconResolver,
    ):
        super().__init__()
        self._group = group
        self._modified_count = modified_count
        self._icon_resolver = icon_resolver
        self.setObjectName("categoryCard")
        self.setStyleSheet(stylesheet_loader.load("category_card.qss"))
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(200, 140)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 12)
        outer.setSpacing(6)

        outer.addWidget(self._build_icon_label())

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

    def _build_icon_label(self) -> QLabel:
        """Prefer a custom image if one is registered for this category;
        otherwise fall back to the emoji configured on the group."""
        label = QLabel()
        label.setObjectName("categoryIcon")
        label.setAlignment(Qt.AlignCenter)

        image_path = self._icon_resolver.resolve(self._group.name)

        if image_path is not None:
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    IconSize.CARD, IconSize.CARD,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                label.setPixmap(scaled)
                label.setFixedHeight(IconSize.CARD)
                return label

        label.setText(self._group.icon)
        return label

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.sig_clicked.emit(self._group)

        super().mousePressEvent(event)
