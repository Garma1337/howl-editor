# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.gui.howl_change import HowlChange
from howl_editor.ctr.formats.howl.models import SpuAddrEntry


class SwapBlobCommand(QUndoCommand):
    """
    Replaces a bank or song blob, with optional spu_addrs snapshot for sample operations.

    Covers: replace bank, replace song, add/remove/replace sample, add/remove/replace sequence.
    """

    def __init__(
        self,
        window,
        description: str,
        collection: HowlCollection,
        index: int,
        new_blob: bytes,
        snapshot_spu: bool = False,
        old_spu: list[SpuAddrEntry] | None = None,
    ):
        super().__init__(description)
        self._window = window
        self._collection = collection
        self._index = index
        self._old_blob = self._get_list()[index]
        self._new_blob = new_blob
        # The builder mutates spu_addrs in place before this runs, so the live
        # table is the post-write state and a caller that changed it hands in
        # its own pre-write copy as `old_spu`.
        self._old_spu = self._capture_spu(window, snapshot_spu, old_spu)
        self._new_spu = self._copy(window.hwl.spu_addrs) if self._old_spu is not None else None

    def _capture_spu(
        self, window, snapshot_spu: bool, old_spu: list[SpuAddrEntry] | None,
    ) -> list[SpuAddrEntry] | None:
        if old_spu is not None:
            return self._copy(old_spu)

        if not snapshot_spu:
            return None

        return self._copy(window.hwl.spu_addrs)

    def redo(self):
        self._get_list()[self._index] = self._new_blob
        self._restore(self._new_spu)
        self._window.apply_change(self._change())

    def undo(self):
        self._get_list()[self._index] = self._old_blob
        self._restore(self._old_spu)
        self._window.apply_change(self._change())

    def _change(self) -> HowlChange:
        """The blob is swapped in place, so no index moves and the views can
        repaint the one row this touched. Undo reports the same thing as redo -
        otherwise undoing would reset the UI the edit just left alone."""
        return HowlChange(collection=self._collection, index=self._index)

    def _restore(self, snapshot: list[SpuAddrEntry] | None) -> None:
        """A sample exists only while its slot entry does, so both directions
        move the table with the blob."""
        if snapshot is not None:
            self._window.hwl.spu_addrs[:] = self._copy(snapshot)

    def _copy(self, entries: list[SpuAddrEntry]) -> list[SpuAddrEntry]:
        return [SpuAddrEntry(e.ptr, e.size) for e in entries]

    def _get_list(self) -> list:
        return getattr(self._window.hwl, self._collection)
