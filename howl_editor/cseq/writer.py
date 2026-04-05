# coding: utf-8

from struct import pack, pack_into

from howl_editor.constants import CSEQ_INSTRUMENT_STRUCT, CSEQ_PERCUSSION_STRUCT
from howl_editor.models import CseqFile, CseqSong, CseqTrack, CseqEvent, CSEQ_EVENT_PARAMS
from howl_editor.vlq import write_vlq


class CseqWriter:

    def serialize(self, cseq: CseqFile) -> bytes:
        """Serialize a CseqFile to raw bytes."""
        out = bytearray()
        self._write_header_placeholder(out, cseq)
        self._write_instruments(out, cseq)
        self._write_percussions(out, cseq)
        song_ptr_pos = len(out)
        self._reserve_song_offsets(out, cseq)
        self._pad_to_alignment(out, 4)
        seq_start = len(out)
        song_offsets = self._write_songs(out, cseq, seq_start)
        self._patch_song_offsets(out, song_ptr_pos, song_offsets)
        self._patch_file_size(out)

        return bytes(out)

    def _write_header_placeholder(self, out: bytearray, cseq: CseqFile) -> None:
        out += pack("<IBBh", 0, len(cseq.instruments), len(cseq.percussions), len(cseq.songs))

    def _write_instruments(self, out: bytearray, cseq: CseqFile) -> None:
        for inst in cseq.instruments:
            out += CSEQ_INSTRUMENT_STRUCT.pack(
                inst.flags, inst.volume, inst.time_to_play,
                inst.frequency, inst.sample_id, inst.adsr,
            )

    def _write_percussions(self, out: bytearray, cseq: CseqFile) -> None:
        for perc in cseq.percussions:
            out += CSEQ_PERCUSSION_STRUCT.pack(
                perc.flags, perc.volume, perc.frequency,
                perc.sample_id, perc.time_to_play,
            )

    def _reserve_song_offsets(self, out: bytearray, cseq: CseqFile) -> None:
        out += b"\x00" * (len(cseq.songs) * 2)

    def _pad_to_alignment(self, out: bytearray, alignment: int) -> None:
        remainder = len(out) % alignment
        if remainder:
            out += b"\x00" * (alignment - remainder)

    def _write_songs(self, out: bytearray, cseq: CseqFile, seq_start: int) -> list[int]:
        offsets = []

        for song in cseq.songs:
            offsets.append(len(out) - seq_start)
            self._write_song(out, song)
        
        return offsets

    def _write_song(self, out: bytearray, song: CseqSong) -> None:
        out += pack("<BBhh", song.unk0, len(song.tracks), song.bpm, song.tpqn)
        track_ptr_pos = len(out)
        out += b"\x00" * (len(song.tracks) * 2)

        header_total = 6 + len(song.tracks) * 2
        remainder = header_total % 4

        if remainder:
            out += b"\x00" * (4 - remainder)

        tracks_start = len(out)
        track_offsets = []

        for track in song.tracks:
            track_offsets.append(len(out) - tracks_start)
            self._write_track(out, track)

        for i, t_off in enumerate(track_offsets):
            pack_into("<H", out, track_ptr_pos + i * 2, t_off)

    def _write_track(self, out: bytearray, track: CseqTrack) -> None:
        out += pack("BB", track.flags, track.unk)

        for evt in track.events:
            self._write_event(out, evt)

    def _write_event(self, out: bytearray, evt: CseqEvent) -> None:
        out += write_vlq(evt.delta)
        out += pack("B", evt.event_type)
        num_params = CSEQ_EVENT_PARAMS.get(evt.event_type, 0)
        
        if num_params >= 1:
            out += pack("B", evt.pitch)
        
        if num_params >= 2:
            out += pack("B", evt.velocity)

    def _patch_song_offsets(self, out: bytearray, ptr_pos: int, offsets: list[int]) -> None:
        for i, offset in enumerate(offsets):
            pack_into("<h", out, ptr_pos + i * 2, offset)

    def _patch_file_size(self, out: bytearray) -> None:
        pack_into("<I", out, 0, len(out))
