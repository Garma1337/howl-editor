# coding: utf-8

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import CseqSong
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.writer import CseqWriter


class CseqEditor:

    def __init__(self, cseq_reader: CseqReader, cseq_writer: CseqWriter):
        self._reader = cseq_reader
        self._writer = cseq_writer

    def update_instrument(
        self, song_data: bytes, inst_index: int, volume: int, frequency: int,
        adsr: int | None = None,
    ) -> bytes:
        """Mutate the named CseqInstrument's volume / frequency (and optionally
        ADSR register) and rewrite the CSEQ blob. Out-of-range numeric inputs
        are silently clamped to the byte (volume) / uint16 (frequency) / uint32
        (adsr) widths the on-wire format supports. Passing adsr=None leaves the
        envelope untouched."""
        cseq = self._reader.read(song_data)

        if inst_index < 0 or inst_index >= len(cseq.instruments):
            raise IndexError(f"Instrument index {inst_index} out of range")

        inst = cseq.instruments[inst_index]
        inst.volume = max(0, min(cseq_fmt.MAX_VOLUME, volume))
        inst.frequency = max(0, min(cseq_fmt.MAX_PITCH_REGISTER, frequency))
        
        if adsr is not None:
            inst.adsr = max(0, min(cseq_fmt.MAX_ADSR_REGISTER, adsr))

        return self._writer.serialize(cseq)

    def update_percussion(
        self, song_data: bytes, perc_index: int, volume: int, frequency: int,
    ) -> bytes:
        """Same as update_instrument but for the percussion table."""
        cseq = self._reader.read(song_data)

        if perc_index < 0 or perc_index >= len(cseq.percussions):
            raise IndexError(f"Percussion index {perc_index} out of range")

        perc = cseq.percussions[perc_index]
        perc.volume = max(0, min(cseq_fmt.MAX_VOLUME, volume))
        perc.frequency = max(0, min(cseq_fmt.MAX_PITCH_REGISTER, frequency))
        return self._writer.serialize(cseq)

    def retarget_instrument(
        self, song_data: bytes, inst_index: int, new_sample_id: int,
    ) -> bytes:
        """Point one instrument at a different SPU index without touching
        its other fields. Lets a music maker swap which sample an instrument
        sounds like in one click instead of exporting + reimporting VAGs."""
        cseq = self._reader.read(song_data)

        if inst_index < 0 or inst_index >= len(cseq.instruments):
            raise IndexError(f"Instrument index {inst_index} out of range")

        cseq.instruments[inst_index].sample_id = new_sample_id
        return self._writer.serialize(cseq)

    def retarget_percussion(
        self, song_data: bytes, perc_index: int, new_sample_id: int,
    ) -> bytes:
        """Same as retarget_instrument but for the percussion table."""
        cseq = self._reader.read(song_data)

        if perc_index < 0 or perc_index >= len(cseq.percussions):
            raise IndexError(f"Percussion index {perc_index} out of range")

        cseq.percussions[perc_index].sample_id = new_sample_id
        return self._writer.serialize(cseq)

    def replace_track_events(
        self, song_data: bytes, seq_index: int, track_index: int, new_events,
    ) -> bytes:
        """Swap one track's CSEQ event list while preserving its flags,
        unk byte, and instrument binding. Used by the per-track MIDI
        import flow — the new event stream must already start with the
        right CHANGE_PATCH and end with END_TRACK."""
        cseq = self._reader.read(song_data)

        if seq_index < 0 or seq_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {seq_index} out of range")

        song = cseq.songs[seq_index]

        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError(f"Track index {track_index} out of range")

        song.tracks[track_index].events = list(new_events)
        return self._writer.serialize(cseq)

    def append_sequence(self, song_data: bytes, new_seq: CseqSong) -> bytes:
        """Append a sequence to a CSEQ blob and return the new blob."""
        cseq = self._reader.read(song_data)
        cseq.songs.append(new_seq)
        return self._writer.serialize(cseq)

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

    def move_sequence(self, song_data: bytes, from_index: int, to_index: int) -> bytes:
        """Move a sequence from one position to another and return the new blob."""
        cseq = self._reader.read(song_data)

        if from_index < 0 or from_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {from_index} out of range (0..{len(cseq.songs) - 1})")

        if to_index < 0 or to_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {to_index} out of range (0..{len(cseq.songs) - 1})")

        seq = cseq.songs.pop(from_index)
        cseq.songs.insert(to_index, seq)
        return self._writer.serialize(cseq)
