# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.gui.howl_change import HowlChange


class RemoveItemCommand(QUndoCommand):
    """Removes a bank or song by index, re-inserts on undo."""

    def __init__(self, window, description: str, collection: HowlCollection, index: int):
        super().__init__(description)
        self._window = window
        self._collection = collection
        self._index = index
        self._data = self._get_list()[index]

    def redo(self):
        del self._get_list()[self._index]
        self._window.apply_change(self._change())

    def undo(self):
        self._get_list().insert(self._index, self._data)
        self._window.apply_change(self._change())

    def _change(self) -> HowlChange:
        return HowlChange(
            collection=self._collection, index=self._index, structural=True,
        )

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
