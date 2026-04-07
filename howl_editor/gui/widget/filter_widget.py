# coding: utf-8

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QTreeWidgetItem


class FilterWidget(QWidget):
    """Search/filter bar that hides non-matching tree items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tree = None
        self._saved_expanded: set[int] = set()
        self._is_filtering = False

    def set_tree(self, tree) -> None:
        self._tree = tree

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Filter (name, SPU index, type...)")
        self._input.setClearButtonEnabled(True)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(50)
        self._clear_btn.clicked.connect(self._clear)
        layout.addWidget(self._clear_btn)

    def reset(self) -> None:
        self._input.clear()
        self._saved_expanded.clear()
        self._is_filtering = False

    def _clear(self) -> None:
        self._input.clear()

    def _on_text_changed(self, text: str) -> None:
        if not self._tree:
            return

        query = text.strip().lower()

        if not query:
            self._restore_all()
            return

        if not self._is_filtering:
            self._save_expanded_state()
            self._is_filtering = True

        self._apply_filter(query)

    def _save_expanded_state(self) -> None:
        self._saved_expanded.clear()
        self._collect_expanded(None)

    def _collect_expanded(self, parent: QTreeWidgetItem | None) -> None:
        count = parent.childCount() if parent else self._tree.topLevelItemCount()

        for i in range(count):
            item = parent.child(i) if parent else self._tree.topLevelItem(i)
            if item.isExpanded():
                self._saved_expanded.add(id(item))
            self._collect_expanded(item)

    def _restore_all(self) -> None:
        """Unhide everything and restore the expanded state from before filtering."""
        self._restore_recursive(None)
        self._saved_expanded.clear()
        self._is_filtering = False

    def _restore_recursive(self, parent: QTreeWidgetItem | None) -> None:
        count = parent.childCount() if parent else self._tree.topLevelItemCount()

        for i in range(count):
            item = parent.child(i) if parent else self._tree.topLevelItem(i)
            item.setHidden(False)
            item.setExpanded(id(item) in self._saved_expanded)
            self._restore_recursive(item)

    def _apply_filter(self, query: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            root = self._tree.topLevelItem(i)
            self._filter_item(root, query)

    def _filter_item(self, item: QTreeWidgetItem, query: str, ancestor_matches: bool = False) -> bool:
        """Filter an item and its children. Returns True if item or any child matches.

        When a parent matches, all its descendants are shown (ancestor_matches=True).
        """
        item_text = (item.text(0) + " " + item.text(1)).lower()
        self_matches = query in item_text
        show_children = ancestor_matches or self_matches

        any_child_matches = False
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filter_item(child, query, show_children):
                any_child_matches = True

        visible = self_matches or any_child_matches or ancestor_matches
        item.setHidden(not visible)

        # Expand to reveal matching children; also expand when the parent
        # itself matched so the user can see its contents.
        if visible and (any_child_matches or self_matches) and item.childCount() > 0:
            item.setExpanded(True)

        return self_matches or any_child_matches
