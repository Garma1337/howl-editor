# coding: utf-8

from PySide6.QtGui import QUndoCommand

from howl_editor.ctr.formats.howl.collections import HowlCollection
from howl_editor.gui.howl_change import HowlChange


class MoveSequenceCommand(QUndoCommand):

    def __init__(self, window, song_index: int, from_index: int, to_index: int):
        super().__init__(f"Move Sequence {from_index} to {to_index} in Song {song_index}")
        self._window = window
        self._song_index = song_index
        self._old_song = window.hwl.songs[song_index]
        self._from = from_index
        self._to = to_index

    def redo(self):
        self._window.hwl.songs[self._song_index] = self._window._services.resolve("cseq_editor").move_sequence(
            self._window.hwl.songs[self._song_index], self._from, self._to,
        )

        self._window.apply_change(self._change())

    def undo(self):
        self._window._services.resolve("howl_editor").replace_song(self._window.hwl, self._song_index, self._old_song)
        self._window.apply_change(self._change())

    def _change(self) -> HowlChange:
        """Sequences within one song are renumbered, so that song's rows have
        to be built again - but no other song moved."""
        return HowlChange(
            collection=HowlCollection.SONGS, index=self._song_index, structural=True,
        )
