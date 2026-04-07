# coding: utf-8

from PySide6.QtGui import QUndoCommand


class MoveSequenceCommand(QUndoCommand):

    def __init__(self, window, song_index: int, from_index: int, to_index: int):
        super().__init__(f"Move Sequence {from_index} to {to_index} in Song {song_index}")
        self._window = window
        self._song_index = song_index
        self._old_song = window.hwl.songs[song_index]
        self._from = from_index
        self._to = to_index

    def redo(self):
        self._window.hwl.songs[self._song_index] = self._window._cseq_editor.move_sequence(
            self._window.hwl.songs[self._song_index], self._from, self._to,
        )

        self._window._rebuild_tree()

    def undo(self):
        self._window._editor.replace_song(self._window.hwl, self._song_index, self._old_song)
        self._window._rebuild_tree()
