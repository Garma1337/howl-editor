# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QLabel, QScrollArea, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from howl_editor.gui.scroll_anchor import ScrollAnchor, ScrollPositionKeeper


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def anchor():
    return ScrollAnchor()


def _settle(turns: int = 4) -> None:
    for _ in range(turns):
        QApplication.processEvents()


class Panel:
    """A scroll area with a hideable strip above it, the shape of the window:
    showing the strip pushes the panel down exactly as a notification does."""

    def __init__(self, anchor, area=None):
        self.root = QWidget()
        layout = QVBoxLayout(self.root)

        self.strip = QLabel("notification")
        self.strip.setFixedHeight(50)
        self.strip.setVisible(False)
        layout.addWidget(self.strip)

        self.area = area if area is not None else self._scroll_area()
        layout.addWidget(self.area)

        self.keeper = anchor.hold(self.area)
        self.root.resize(300, 300)
        self.root.show()
        _settle()

    def _scroll_area(self) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        rows = QVBoxLayout(inner)

        for i in range(60):
            rows.addWidget(QLabel(f"row {i}"))

        area.setWidget(inner)
        return area

    @property
    def offset(self) -> int:
        return self.area.verticalScrollBar().value()

    @offset.setter
    def offset(self, value: int) -> None:
        self.area.verticalScrollBar().setValue(value)
        _settle()

    @property
    def top(self) -> int:
        return self.area.mapTo(self.root, QPoint(0, 0)).y()

    def show_strip(self, visible: bool = True) -> int:
        """Show/hide the strip and report how far the panel moved."""
        before = self.top
        self.strip.setVisible(visible)
        _settle()
        return self.top - before


@pytest.fixture
def panel(qt_app, anchor):
    return Panel(anchor)


def _tree() -> QTreeWidget:
    tree = QTreeWidget()

    for i in range(200):
        QTreeWidgetItem(tree, [f"row {i}", "info"])

    return tree


class TestHoldingPositionThroughAShift:

    def test_content_stays_put_when_something_above_takes_space(self, panel):
        panel.offset = 400
        at_rest = panel.offset

        moved = panel.show_strip()

        assert moved > 0                        # the panel really was pushed down
        assert panel.offset == at_rest + moved  # ...and the content scrolled to match

    def test_content_stays_put_when_the_space_is_given_back(self, panel):
        panel.offset = 400
        panel.show_strip()
        pushed = panel.offset

        moved = panel.show_strip(False)

        assert panel.offset == pushed + moved

    def test_a_panel_at_the_top_is_left_alone(self, panel):
        """There is nothing above the first row to hold in place, and scrolling
        down would hide content the user can see."""
        panel.offset = 0

        panel.show_strip()

        assert panel.offset == 0

    def test_resizing_without_moving_the_panel_does_not_scroll(self, panel):
        """Only the panel being pushed counts. A window resized at the bottom
        leaves the content where it is, so the offset must not move either."""
        panel.offset = 400
        at_rest = panel.offset

        panel.root.resize(300, 240)
        _settle()

        assert panel.offset == at_rest


class TestScrollUnits:
    """An item view can scroll a row at a time, so its scroll bar counts rows.
    Adding a pixel delta to one of those moved the File Browser tree by that
    many rows."""

    def test_a_tree_scrolling_per_item_is_left_alone(self, qt_app, anchor):
        tree = _tree()
        tree.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        panel = Panel(anchor, area=tree)
        panel.offset = 20
        at_rest = panel.offset

        panel.show_strip()

        assert panel.offset == at_rest

    def test_a_tree_scrolling_per_pixel_is_held_still(self, qt_app, anchor):
        tree = _tree()
        tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        panel = Panel(anchor, area=tree)
        panel.offset = 400
        at_rest = panel.offset

        moved = panel.show_strip()

        assert moved > 0
        assert panel.offset == at_rest + moved

    def test_a_plain_scroll_area_counts_pixels(self, qt_app):
        assert ScrollPositionKeeper.scrolls_by_pixel(QScrollArea())
