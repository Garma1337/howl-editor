# coding: utf-8

from PySide6.QtCore import QEvent, QObject, QPoint
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea


class ScrollPositionKeeper(QObject):
    """Holds a panel's content still when the panel itself is pushed down.

    A notification bar appears above the tabs, so the panel below it moves down
    and the row the user was reading moves with it. Adding the distance the
    panel moved to the scroll offset cancels that out. This is about layout,
    not about edits: an edit no longer rebuilds the panel it changed, so there
    is nothing to restore afterwards.
    """

    def __init__(self, area: QAbstractScrollArea):
        super().__init__(area)
        self._top = self.panel_top(area)
        area.installEventFilter(self)

    @staticmethod
    def panel_top(area: QAbstractScrollArea) -> int:
        """The panel's top edge inside its window. Moving or resizing the
        window does not change it, so only something taking space above the
        panel does."""
        return area.mapTo(area.window(), QPoint(0, 0)).y()

    @staticmethod
    def scrolls_by_pixel(area: QAbstractScrollArea) -> bool:
        """An item view can scroll a row at a time, which makes its scroll bar
        count rows rather than pixels - a 54-pixel shift would move such a view
        54 rows."""
        if not isinstance(area, QAbstractItemView):
            return True

        return area.verticalScrollMode() == QAbstractItemView.ScrollPerPixel

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Move, QEvent.Resize):
            self._absorb_shift()

        return False

    def _absorb_shift(self) -> None:
        area = self.parent()
        previous, self._top = self._top, self.panel_top(area)
        delta = self._top - previous

        # The baseline above moves either way; this only decides whether to
        # compensate. An offset counted in rows cannot absorb a pixel delta.
        if delta == 0 or not area.isVisible() or not self.scrolls_by_pixel(area):
            return

        bar = area.verticalScrollBar()

        # At the top there is nothing above the first row to hold in place.
        if bar.value() > 0:
            bar.setValue(bar.value() + delta)


class ScrollAnchor:

    def hold(self, area: QAbstractScrollArea) -> ScrollPositionKeeper:
        return ScrollPositionKeeper(area)
