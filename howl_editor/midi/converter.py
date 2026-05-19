# coding: utf-8

from pathlib import Path

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import (
    CseqFile, CseqSong, CseqTrack, CseqEvent, CseqEventType, CseqInstrument, CseqPercussion
)
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from howl_editor.midi import format as midi_fmt
from howl_editor.midi.drum_pitch_remapper import DrumPitchRemapper
from howl_editor.midi.mido_message_type import MidoMessageType
from howl_editor.midi.models import (
    MidiInfo, MidiTrackInfo, MidiConvertSettings, InstrumentMapping, DrumPitchMapping,
)


class MidiConverter:

    def __init__(self, cseq_writer: CseqWriter, drum_pitch_remapper: DrumPitchRemapper):
        self._cseq_writer = cseq_writer
        self._drum_remapper = drum_pitch_remapper

    def extract_track_events(
        self, midi_path: str | Path, midi_track_index: int,
        instrument_index: int,
    ) -> list[CseqEvent]:
        """Convert one MIDI track's messages into a CSEQ event list ready to
        slot into an existing CseqTrack. Output is bracketed by a leading
        CHANGE_PATCH pointing at instrument_index and a trailing END_TRACK,
        matching what `CseqEditor.replace_track_events` expects.

        No drum-pitch remapping is applied — for per-track import the user
        is responsible for picking a track whose pitch usage matches the
        target's percussion table (or for melodic targets, where pitches
        pass through 1:1)."""
        self._check_mido()
        mid = mido.MidiFile(str(midi_path))

        if midi_track_index < 0 or midi_track_index >= len(mid.tracks):
            raise IndexError(
                f"MIDI track {midi_track_index} out of range (0..{len(mid.tracks) - 1})",
            )

        midi_track = mid.tracks[midi_track_index]
        events: list[CseqEvent] = [CseqEvent(
            delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=instrument_index,
        )]

        last_tick = 0
        current_tick = 0

        for msg in midi_track:
            current_tick += msg.time
            event = self._convert_message(msg, current_tick, last_tick, None)

            if event is not None:
                events.append(event)
                last_tick = current_tick

        events.append(CseqEvent(delta=0, event_type=CseqEventType.END_TRACK))
        return events

    def get_midi_info(self, midi_path: str | Path) -> MidiInfo:
        """Extract structured info about a MIDI file."""
        self._check_mido()
        mid = mido.MidiFile(str(midi_path))
        tracks = []

        for i, track in enumerate(mid.tracks):
            note_count = sum(1 for msg in track if msg.type == MidoMessageType.NOTE_ON)
            channels = sorted({msg.channel for msg in track if hasattr(msg, "channel")})
            drum_pitches = self._drum_remapper.collect_drum_pitches(track)
            tracks.append(MidiTrackInfo(
                index=i,
                name=track.name or f"Track {i}",
                note_count=note_count,
                channels=channels,
                drum_pitches=drum_pitches,
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
        inst_map, drum_pitch_tables = self._create_instruments(cseq, midi_tracks, settings)

        for track_idx, (midi_idx, midi_track) in enumerate(midi_tracks):
            cseq_track = self._convert_track(
                midi_track, track_idx, inst_map, drum_pitch_tables,
            )
            song.tracks.append(cseq_track)

        cseq.songs.append(song)
        return cseq

    def _extract_tempo(self, mid, song: CseqSong) -> None:
        for track in mid.tracks:
            for msg in track:
                if msg.type == MidoMessageType.SET_TEMPO:
                    song.bpm = max(1, int(mido.tempo2bpm(msg.tempo)))
                    return

    def _collect_note_tracks(self, mid) -> list[tuple[int, list]]:
        return [
            (i, track) for i, track in enumerate(mid.tracks)
            if any(msg.type in (MidoMessageType.NOTE_ON, MidoMessageType.NOTE_OFF) for msg in track)
        ]

    def _create_instruments(
        self, cseq: CseqFile, midi_tracks: list, settings: MidiConvertSettings,
    ) -> tuple[dict[int, int], dict[int, list[int]]]:
        """Populate the CSEQ instrument and percussion lists.

        Returns:
          - instrument_map: cseq track index → instrument/percussion index.
            For drum tracks this points at the FIRST percussion entry; the
            actual per-note index is resolved via drum_pitch_tables.
          - drum_pitch_tables: cseq track index → ordered MIDI pitch list,
            used by `_convert_track` to rewrite NOTE_ON pitches into CSEQ
            percussion indices.
        """
        instrument_map: dict[int, int] = {}
        drum_pitch_tables: dict[int, list[int]] = {}

        for track_idx, (midi_idx, midi_track) in enumerate(midi_tracks):
            mapping = settings.mappings[midi_idx] if midi_idx < len(settings.mappings) else InstrumentMapping()

            if mapping.is_drum:
                pitch_table = self._build_drum_pitch_table(midi_track, mapping)
                first_perc_index = len(cseq.percussions)

                for pitch in pitch_table:
                    slot = self._find_drum_slot(mapping, pitch)
                    cseq.percussions.append(CseqPercussion(
                        flags=1,
                        volume=slot.volume,
                        frequency=slot.frequency,
                        sample_id=slot.sample_id,
                    ))

                instrument_map[track_idx] = first_perc_index
                drum_pitch_tables[track_idx] = pitch_table
            else:
                cseq.instruments.append(CseqInstrument(
                    flags=1,
                    volume=mapping.volume,
                    frequency=mapping.frequency,
                    sample_id=mapping.sample_id,
                    adsr=mapping.adsr,
                ))

                instrument_map[track_idx] = len(cseq.instruments) - 1

        return instrument_map, drum_pitch_tables

    def _build_drum_pitch_table(self, midi_track, mapping: InstrumentMapping) -> list[int]:
        """Decide the order of percussion slots for a drum track. Priority:
        1. Explicit per-pitch dialog mappings (preserves user-chosen ordering
           so SPU sample IDs line up).
        2. Unique pitches on the GM drum channel.
        3. All unique note pitches in the track — when the user manually marks
           a non-channel-9 track as drum we still need a pitch table.
        """
        if mapping.drum_pitches:
            return [slot.midi_pitch for slot in mapping.drum_pitches]

        drum_channel_pitches = self._drum_remapper.collect_drum_pitches(midi_track)
        if drum_channel_pitches:
            return drum_channel_pitches

        return self._drum_remapper.collect_all_note_pitches(midi_track)

    def _find_drum_slot(self, mapping: InstrumentMapping, midi_pitch: int):
        for slot in mapping.drum_pitches:
            if slot.midi_pitch == midi_pitch:
                return slot

        return DrumPitchMapping(
            midi_pitch=midi_pitch,
            sample_id=mapping.sample_id,
            frequency=mapping.frequency,
            volume=mapping.volume,
        )

    def _convert_track(
        self, midi_track, track_idx: int,
        instrument_map: dict, drum_pitch_tables: dict[int, list[int]],
    ) -> CseqTrack:
        pitch_table = drum_pitch_tables.get(track_idx)
        is_drum = pitch_table is not None
        cseq_track = CseqTrack(flags=1 if is_drum else 0)
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
            event = self._convert_message(msg, current_tick, last_tick, pitch_table)

            if event:
                cseq_track.events.append(event)
                last_tick = current_tick

        cseq_track.events.append(CseqEvent(delta=0, event_type=CseqEventType.END_TRACK))
        return cseq_track

    def _convert_message(
        self, msg, current_tick: int, last_tick: int,
        drum_pitch_table: list[int] | None,
    ) -> CseqEvent | None:
        delta = current_tick - last_tick

        if msg.type == MidoMessageType.NOTE_ON and msg.velocity > 0:
            return CseqEvent(
                delta=delta, event_type=CseqEventType.NOTE_ON,
                pitch=self._note_pitch(msg.note, drum_pitch_table),
                velocity=msg.velocity,
            )

        if msg.type == MidoMessageType.NOTE_OFF or (msg.type == MidoMessageType.NOTE_ON and msg.velocity == 0):
            return CseqEvent(
                delta=delta, event_type=CseqEventType.NOTE_OFF,
                pitch=self._note_pitch(msg.note, drum_pitch_table),
            )

        if msg.type == MidoMessageType.CONTROL_CHANGE:
            if msg.control == midi_fmt.CC_VOLUME:
                return CseqEvent(
                    delta=delta, event_type=CseqEventType.VELOCITY,
                    pitch=self._midi_cc_to_cseq_byte(msg.value),
                )

            if msg.control == midi_fmt.CC_PAN:
                return CseqEvent(
                    delta=delta, event_type=CseqEventType.PAN,
                    pitch=self._midi_cc_to_cseq_byte(msg.value),
                )

        if msg.type == MidoMessageType.PITCHWHEEL:
            bend = self._midi_bend_to_cseq(msg.pitch)
            return CseqEvent(delta=delta, event_type=CseqEventType.PITCH_BEND, pitch=bend)

        return None

    def _midi_bend_to_cseq(self, midi_pitch: int) -> int:
        return max(0, min(cseq_fmt.MAX_PITCH_BEND, int((midi_pitch + midi_fmt.PITCH_BEND_CENTER) / midi_fmt.PITCH_BEND_RANGE * cseq_fmt.MAX_PITCH_BEND)))

    def _midi_cc_to_cseq_byte(self, midi_value: int) -> int:
        clamped = max(0, min(midi_fmt.CC_MAX, midi_value))
        return int(clamped / midi_fmt.CC_MAX * cseq_fmt.CC_MAX)

    def _note_pitch(self, midi_note: int, drum_pitch_table: list[int] | None) -> int:
        if drum_pitch_table is None:
            return midi_note

        if midi_note in drum_pitch_table:
            return self._drum_remapper.remap(midi_note, drum_pitch_table)

        return midi_note
