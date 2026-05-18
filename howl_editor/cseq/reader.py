# coding: utf-8

from struct import unpack_from

from howl_editor.analysis.stock_name_resolver import StockNameResolver
from howl_editor.core.vlq import VlqCodec
from howl_editor.models import (
    CseqFile, CseqInstrument, CseqPercussion, CseqInfo,
    CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CSEQ_EVENT_PARAMS, CSEQ_TERMINAL_EVENTS,
)

_OFFSET_SIZE = 2
_SONG_HEADER_SIZE = 6
_TRACK_HEADER_SIZE = 2
_ALIGNMENT = 4


class CseqReader:

    def __init__(self, vlq_codec: VlqCodec, stock_names: StockNameResolver):
        self._vlq = vlq_codec
        self._name_resolver = stock_names

    def get_name(self, index: int) -> str:
        return self._name_resolver.song_name(index)

    def read(self, data: bytes) -> CseqFile:
        """Parse raw CSEQ bytes into a CseqFile."""
        self._validate_min_size(data)
        file_size, num_inst, num_perc, num_songs = self._parse_header(data)
        pos = CseqInfo.HEADER_SIZE

        instruments, pos = self._parse_instruments(data, pos, num_inst)
        percussions, pos = self._parse_percussions(data, pos, num_perc)
        song_offsets, pos = self._parse_song_offsets(data, pos, num_songs)
        pos = self._align_to(pos, _ALIGNMENT)

        seq_start = pos
        songs = [self._parse_song(data, seq_start, offset) for offset in song_offsets]

        return CseqFile(instruments=instruments, percussions=percussions, songs=songs)

    def get_info(self, data: bytes) -> CseqInfo:
        """Get lightweight summary without full parse."""
        if len(data) < CseqInfo.HEADER_SIZE:
            return CseqInfo()

        file_size, num_inst, num_perc, num_songs = self._parse_header(data)
        
        return CseqInfo(
            file_size=file_size,
            num_instruments=num_inst,
            num_percussions=num_perc,
            num_songs=num_songs,
        )

    def _validate_min_size(self, data: bytes) -> None:
        if len(data) < CseqInfo.HEADER_SIZE:
            raise ValueError(f"CSEQ data too small: {len(data)} < {CseqInfo.HEADER_SIZE}")

    def _parse_header(self, data: bytes) -> tuple[int, int, int, int]:
        return CseqInfo.HEADER_STRUCT.unpack_from(data, 0)

    def _parse_instruments(self, data: bytes, pos: int, count: int) -> tuple[list[CseqInstrument], int]:
        instruments = []
        for _ in range(count):
            flags, volume, ttp, freq, sid, adsr = CseqInstrument.STRUCT.unpack_from(data, pos)
            instruments.append(CseqInstrument(flags, volume, ttp, freq, sid, adsr))
            pos += CseqInstrument.SIZE
        
        return instruments, pos

    def _parse_percussions(self, data: bytes, pos: int, count: int) -> tuple[list[CseqPercussion], int]:
        percussions = []
        
        for _ in range(count):
            flags, volume, freq, sid, ttp = CseqPercussion.STRUCT.unpack_from(data, pos)
            percussions.append(CseqPercussion(flags, volume, freq, sid, ttp))
            pos += CseqPercussion.SIZE
        
        return percussions, pos

    def _parse_song_offsets(self, data: bytes, pos: int, count: int) -> tuple[list[int], int]:
        offsets = []

        for _ in range(count):
            offset, = unpack_from("<h", data, pos)
            offsets.append(offset)
            pos += _OFFSET_SIZE
        
        return offsets, pos

    def _align_to(self, pos: int, alignment: int) -> int:
        remainder = pos % alignment
        return pos + (alignment - remainder) if remainder else pos

    def _parse_song(self, data: bytes, seq_start: int, offset: int) -> CseqSong:
        pos = seq_start + offset
        unk0, track_num, bpm, tpqn = unpack_from("<BBhh", data, pos)
        pos += _SONG_HEADER_SIZE

        track_offsets = []
        for _ in range(track_num):
            t_off, = unpack_from("<H", data, pos)
            track_offsets.append(t_off)
            pos += _OFFSET_SIZE

        header_total = _SONG_HEADER_SIZE + track_num * _OFFSET_SIZE
        tracks_start = self._align_to(seq_start + offset + header_total, _ALIGNMENT)

        tracks = [self._parse_track(data, tracks_start, t_off) for t_off in track_offsets]
        return CseqSong(unk0=unk0, bpm=bpm, tpqn=tpqn, tracks=tracks)

    def _parse_track(self, data: bytes, tracks_start: int, offset: int) -> CseqTrack:
        pos = tracks_start + offset
        flags = data[pos]
        unk = data[pos + 1]
        pos += _TRACK_HEADER_SIZE

        track = CseqTrack(flags=flags, unk=unk)
        while pos < len(data):
            event, pos = self._parse_event(data, pos)
            
            if event.event_type == CseqEventType.CHANGE_PATCH:
                track.instrument = event.pitch
            
            track.events.append(event)
            if event.event_type in CSEQ_TERMINAL_EVENTS:
                break
        
        return track

    def _parse_event(self, data: bytes, pos: int) -> tuple[CseqEvent, int]:
        delta, pos = self._vlq.read(data, pos)
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
