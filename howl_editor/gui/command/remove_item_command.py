# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection


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
        self._window._rebuild_tree()

    def undo(self):
        self._get_list().insert(self._index, self._data)
        self._window._rebuild_tree()

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
