# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.models import SpuAddrEntry


class SwapBlobCommand(QUndoCommand):
    """
    Replaces a bank or song blob, with optional spu_addrs snapshot for sample operations.

    Covers: replace bank, replace song, add/remove/replace sample, add/remove/replace sequence.
    """

    def __init__(self, window, description: str, collection: str, index: int, new_blob: bytes, snapshot_spu: bool = False):
        super().__init__(description)
        self._window = window
        self._collection = collection
        self._index = index
        self._old_blob = self._get_list()[index]
        self._new_blob = new_blob
        self._old_spu = [SpuAddrEntry(e.ptr, e.size) for e in window.hwl.spu_addrs] if snapshot_spu else None

    def redo(self):
        self._get_list()[self._index] = self._new_blob
        self._window._rebuild_tree()

    def undo(self):
        self._get_list()[self._index] = self._old_blob

        if self._old_spu is not None:
            self._window.hwl.spu_addrs[:] = [SpuAddrEntry(e.ptr, e.size) for e in self._old_spu]

        self._window._rebuild_tree()

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
