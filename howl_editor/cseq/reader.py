# coding: utf-8

from struct import unpack_from

from howl_editor.constants import (
    CSEQ_HEADER_STRUCT, CSEQ_HEADER_SIZE,
    CSEQ_INSTRUMENT_STRUCT, CSEQ_INSTRUMENT_SIZE,
    CSEQ_PERCUSSION_STRUCT, CSEQ_PERCUSSION_SIZE,
)
from howl_editor.models import (
    CseqFile, CseqInstrument, CseqPercussion, CseqInfo,
    CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CSEQ_EVENT_PARAMS, CSEQ_TERMINAL_EVENTS,
)
from howl_editor.vlq import read_vlq


class CseqReader:

    def read(self, data: bytes) -> CseqFile:
        """Parse raw CSEQ bytes into a CseqFile."""
        self._validate_min_size(data)
        file_size, num_inst, num_perc, num_songs = self._parse_header(data)
        pos = CSEQ_HEADER_SIZE

        instruments, pos = self._parse_instruments(data, pos, num_inst)
        percussions, pos = self._parse_percussions(data, pos, num_perc)
        song_offsets, pos = self._parse_song_offsets(data, pos, num_songs)
        pos = self._align_to(pos, 4)

        seq_start = pos
        songs = [self._parse_song(data, seq_start, offset) for offset in song_offsets]

        return CseqFile(instruments=instruments, percussions=percussions, songs=songs)

    def get_info(self, data: bytes) -> CseqInfo:
        """Get lightweight summary without full parse."""
        if len(data) < CSEQ_HEADER_SIZE:
            return CseqInfo()

        file_size, num_inst, num_perc, num_songs = self._parse_header(data)
        
        return CseqInfo(
            file_size=file_size,
            num_instruments=num_inst,
            num_percussions=num_perc,
            num_songs=num_songs,
        )

    def _validate_min_size(self, data: bytes) -> None:
        if len(data) < CSEQ_HEADER_SIZE:
            raise ValueError(f"CSEQ data too small: {len(data)} < {CSEQ_HEADER_SIZE}")

    def _parse_header(self, data: bytes) -> tuple[int, int, int, int]:
        return CSEQ_HEADER_STRUCT.unpack_from(data, 0)

    def _parse_instruments(self, data: bytes, pos: int, count: int) -> tuple[list[CseqInstrument], int]:
        instruments = []
        for _ in range(count):
            flags, volume, ttp, freq, sid, adsr = CSEQ_INSTRUMENT_STRUCT.unpack_from(data, pos)
            instruments.append(CseqInstrument(flags, volume, ttp, freq, sid, adsr))
            pos += CSEQ_INSTRUMENT_SIZE
        
        return instruments, pos

    def _parse_percussions(self, data: bytes, pos: int, count: int) -> tuple[list[CseqPercussion], int]:
        percussions = []
        
        for _ in range(count):
            flags, volume, freq, sid, ttp = CSEQ_PERCUSSION_STRUCT.unpack_from(data, pos)
            percussions.append(CseqPercussion(flags, volume, freq, sid, ttp))
            pos += CSEQ_PERCUSSION_SIZE
        
        return percussions, pos

    def _parse_song_offsets(self, data: bytes, pos: int, count: int) -> tuple[list[int], int]:
        offsets = []

        for _ in range(count):
            offset, = unpack_from("<h", data, pos)
            offsets.append(offset)
            pos += 2
        
        return offsets, pos

    def _align_to(self, pos: int, alignment: int) -> int:
        remainder = pos % alignment
        return pos + (alignment - remainder) if remainder else pos

    def _parse_song(self, data: bytes, seq_start: int, offset: int) -> CseqSong:
        pos = seq_start + offset
        unk0, track_num, bpm, tpqn = unpack_from("<BBhh", data, pos)
        pos += 6

        track_offsets = []
        for _ in range(track_num):
            t_off, = unpack_from("<H", data, pos)
            track_offsets.append(t_off)
            pos += 2

        header_total = 6 + track_num * 2
        tracks_start = self._align_to(seq_start + offset + header_total, 4)

        tracks = [self._parse_track(data, tracks_start, t_off) for t_off in track_offsets]
        return CseqSong(unk0=unk0, bpm=bpm, tpqn=tpqn, tracks=tracks)

    def _parse_track(self, data: bytes, tracks_start: int, offset: int) -> CseqTrack:
        pos = tracks_start + offset
        track_type, = unpack_from("<H", data, pos)
        pos += 2

        track = CseqTrack(track_type=track_type)
        while pos < len(data):
            event, pos = self._parse_event(data, pos)
            
            if event.event_type == CseqEventType.CHANGE_PATCH:
                track.instrument = event.pitch
            
            track.events.append(event)
            if event.event_type in CSEQ_TERMINAL_EVENTS:
                break
        
        return track

    def _parse_event(self, data: bytes, pos: int) -> tuple[CseqEvent, int]:
        delta, pos = read_vlq(data, pos)
        evt_byte = data[pos]
        pos += 1

        try:
            evt_type = CseqEventType(evt_byte)
        except ValueError:
            return CseqEvent(delta=delta, event_type=CseqEventType.END_TRACK), pos

        pitch = 0
        velocity = 0
        num_params = CSEQ_EVENT_PARAMS.get(evt_type, 0)

        if num_params >= 1 and pos < len(data):
            pitch = data[pos]
            pos += 1
        
        if num_params >= 2 and pos < len(data):
            velocity = data[pos]
            pos += 1

        return CseqEvent(delta=delta, event_type=evt_type, pitch=pitch, velocity=velocity), pos
