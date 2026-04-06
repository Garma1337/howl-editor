# coding: utf-8

from howl_editor.cseq.reader import CseqReader
from howl_editor.cseq.writer import CseqWriter
from howl_editor.models import CseqSong


class CseqEditor:

    def __init__(self, cseq_reader: CseqReader, cseq_writer: CseqWriter):
        self._reader = cseq_reader
        self._writer = cseq_writer

    def replace_sequence(self, song_data: bytes, seq_index: int, new_seq: CseqSong) -> bytes:
        """Replace a single sequence in a CSEQ blob and return the new blob."""
        cseq = self._reader.read(song_data)

        if seq_index < 0 or seq_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {seq_index} out of range (0..{len(cseq.songs) - 1})")

        cseq.songs[seq_index] = new_seq
        return self._writer.serialize(cseq)

    def remove_sequence(self, song_data: bytes, seq_index: int) -> bytes:
        """Remove a single sequence from a CSEQ blob and return the new blob."""
        cseq = self._reader.read(song_data)

        if seq_index < 0 or seq_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {seq_index} out of range (0..{len(cseq.songs) - 1})")

        del cseq.songs[seq_index]
        return self._writer.serialize(cseq)
