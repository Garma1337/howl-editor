# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection


class MoveItemCommand(QUndoCommand):
    """Moves a bank or song between positions, reverses on undo."""

    def __init__(self, window, description: str, collection: HowlCollection, from_index: int, to_index: int):
        super().__init__(description)
        self._window = window
        self._collection = collection
        self._from = from_index
        self._to = to_index

    def redo(self):
        items = self._get_list()
        item = items.pop(self._from)
        items.insert(self._to, item)

        self._window._rebuild_tree()

    def undo(self):
        items = self._get_list()
        item = items.pop(self._to)
        items.insert(self._from, item)

        self._window._rebuild_tree()

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
