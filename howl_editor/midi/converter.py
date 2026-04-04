# coding: utf-8

from pathlib import Path

from howl_editor.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType,
    CseqInstrument, CseqPercussion,
)
from howl_editor.cseq.writer import CseqWriter
from howl_editor.midi.models import MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False


class MidiConverter:

    def __init__(self, cseq_writer: CseqWriter):
        self._cseq_writer = cseq_writer

    def get_midi_info(self, midi_path: str | Path) -> MidiInfo:
        """Extract structured info about a MIDI file."""
        self._check_mido()
        mid = mido.MidiFile(str(midi_path))
        tracks = []

        for i, track in enumerate(mid.tracks):
            note_count = sum(1 for msg in track if msg.type == "note_on")
            channels = sorted({msg.channel for msg in track if hasattr(msg, "channel")})
            tracks.append(MidiTrackInfo(
                index=i,
                name=track.name or f"Track {i}",
                note_count=note_count,
                channels=channels,
            ))
        
        return MidiInfo(
            midi_type=mid.type,
            ticks_per_beat=mid.ticks_per_beat,
            num_tracks=len(mid.tracks),
            tracks=tracks,
        )

    def convert(self, midi_path: str | Path, settings: MidiConvertSettings) -> bytes:
        """Convert a MIDI file to CSEQ bytes."""
        cseq = self.convert_to_model(midi_path, settings)
        return self._cseq_writer.serialize(cseq)

    def convert_to_model(self, midi_path: str | Path, settings: MidiConvertSettings) -> CseqFile:
        """Convert a MIDI file to a CseqFile model."""
        self._check_mido()
        mid = mido.MidiFile(str(midi_path))
        return self._build_cseq(mid, settings)

    def _check_mido(self) -> None:
        if not HAS_MIDO:
            raise RuntimeError("mido library required. Install with: pip install mido")

    def _build_cseq(self, mid, settings: MidiConvertSettings) -> CseqFile:
        cseq = CseqFile()
        song = CseqSong(tpqn=mid.ticks_per_beat, bpm=settings.default_bpm)
        self._extract_tempo(mid, song)

        midi_tracks = self._collect_note_tracks(mid)
        inst_map, drum_set = self._create_instruments(cseq, midi_tracks, settings)

        for track_idx, (midi_idx, midi_track) in enumerate(midi_tracks):
            cseq_track = self._convert_track(midi_track, track_idx, inst_map, drum_set)
            song.tracks.append(cseq_track)

        cseq.songs.append(song)
        return cseq

    def _extract_tempo(self, mid, song: CseqSong) -> None:
        for track in mid.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    song.bpm = max(1, int(mido.tempo2bpm(msg.tempo)))
                    return

    def _collect_note_tracks(self, mid) -> list[tuple[int, list]]:
        return [
            (i, track) for i, track in enumerate(mid.tracks)
            if any(msg.type in ("note_on", "note_off") for msg in track)
        ]

    def _create_instruments(
        self, cseq: CseqFile, midi_tracks: list, settings: MidiConvertSettings,
    ) -> tuple[dict[int, int], set[int]]:
        instrument_map: dict[int, int] = {}
        drum_set: set[int] = set()
        
        for track_idx, (midi_idx, _) in enumerate(midi_tracks):
            mapping = settings.mappings[midi_idx] if midi_idx < len(settings.mappings) else InstrumentMapping()

            if mapping.is_drum:
                drum_set.add(track_idx)
                
                cseq.percussions.append(CseqPercussion(
                    flags=1, 
                    volume=mapping.volume,
                    frequency=mapping.frequency, 
                    sample_id=mapping.sample_id,
                ))
            
                instrument_map[track_idx] = len(cseq.percussions) - 1
            else:
                cseq.instruments.append(CseqInstrument(
                    flags=1, 
                    volume=mapping.volume,
                    frequency=mapping.frequency, 
                    sample_id=mapping.sample_id,
                    adsr=mapping.adsr,
                ))
                
                instrument_map[track_idx] = len(cseq.instruments) - 1
        
        return instrument_map, drum_set

    def _convert_track(
        self, midi_track, track_idx: int, instrument_map: dict, drum_set: set,
    ) -> CseqTrack:
        is_drum = track_idx in drum_set
        cseq_track = CseqTrack(track_type=1 if is_drum else 0)
        patch_idx = instrument_map.get(track_idx, 0)

        cseq_track.events.append(CseqEvent(
            delta=0, 
            event_type=CseqEventType.CHANGE_PATCH, 
            pitch=patch_idx,
        ))

        cseq_track.instrument = patch_idx

        last_tick = 0
        current_tick = 0
        
        for msg in midi_track:
            current_tick += msg.time
            event = self._convert_message(msg, current_tick, last_tick)
            
            if event:
                cseq_track.events.append(event)
                last_tick = current_tick

        cseq_track.events.append(CseqEvent(delta=0, event_type=CseqEventType.END_TRACK))
        return cseq_track

    def _convert_message(self, msg, current_tick: int, last_tick: int) -> CseqEvent | None:
        delta = current_tick - last_tick

        if msg.type == "note_on" and msg.velocity > 0:
            return CseqEvent(
                delta=delta, event_type=CseqEventType.NOTE_ON,
                pitch=msg.note, velocity=msg.velocity,
            )

        if msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            return CseqEvent(delta=delta, event_type=CseqEventType.NOTE_OFF, pitch=msg.note)

        if msg.type == "control_change":
            if msg.control == 7:
                return CseqEvent(delta=delta, event_type=CseqEventType.VELOCITY, pitch=msg.value)

            if msg.control == 10:
                return CseqEvent(delta=delta, event_type=CseqEventType.PAN, pitch=msg.value)

        if msg.type == "pitchwheel":
            bend = max(0, min(255, int((msg.pitch + 8192) / 16384 * 255)))
            return CseqEvent(delta=delta, event_type=CseqEventType.PITCH_BEND, pitch=bend)

        return None
