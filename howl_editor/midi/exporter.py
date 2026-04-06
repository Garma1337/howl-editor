# coding: utf-8

import io
from pathlib import Path

from howl_editor.models import CseqFile, CseqSong, CseqTrack, CseqEventType

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

_DRUM_CHANNEL = 9
_MAX_MIDI_CHANNEL = 15
_MIDI_CC_VOLUME = 7
_MIDI_CC_PAN = 10
_CSEQ_MAX_PITCH_BEND = 255
_MIDI_PITCH_BEND_RANGE = 16384
_MIDI_PITCH_BEND_CENTER = 8192


class CseqMidiExporter:

    def export(self, cseq: CseqFile, song_index: int = 0) -> bytes:
        if not HAS_MIDO:
            raise RuntimeError("mido is required for MIDI export")

        if song_index >= len(cseq.songs):
            raise ValueError(f"Song index {song_index} out of range (0..{len(cseq.songs) - 1})")

        mid = self._build_midi(cseq.songs[song_index])
        buf = io.BytesIO()
        mid.save(file=buf)
        return buf.getvalue()

    def export_to_file(self, cseq: CseqFile, path: str | Path, song_index: int = 0) -> None:
        Path(path).write_bytes(self.export(cseq, song_index))

    def _build_midi(self, song: CseqSong) -> 'mido.MidiFile':
        mid = mido.MidiFile(type=1, ticks_per_beat=song.tpqn)

        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(song.bpm), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        next_channel = 0
        for track in song.tracks:
            channel, next_channel = self._assign_channel(track.is_drum, next_channel)
            midi_track = self._convert_track(track, channel)
            mid.tracks.append(midi_track)

        return mid

    def _assign_channel(self, is_drum: bool, next_channel: int) -> tuple[int, int]:
        if is_drum:
            return _DRUM_CHANNEL, next_channel

        channel = next_channel
        if next_channel == _DRUM_CHANNEL:
            next_channel += 1
        next_channel += 1

        if next_channel > _MAX_MIDI_CHANNEL:
            next_channel = 0

        return channel, next_channel

    def _convert_track(self, track: CseqTrack, channel: int) -> 'mido.MidiTrack':
        midi_track = mido.MidiTrack()

        for event in track.events:
            delta = event.delta

            if event.event_type == CseqEventType.CHANGE_PATCH:
                midi_track.append(mido.Message(
                    "program_change", program=event.pitch, channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.NOTE_ON:
                midi_track.append(mido.Message(
                    "note_on", note=event.pitch, velocity=event.velocity,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.NOTE_OFF:
                midi_track.append(mido.Message(
                    "note_off", note=event.pitch, velocity=0,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.VELOCITY:
                midi_track.append(mido.Message(
                    "control_change", control=_MIDI_CC_VOLUME, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PAN:
                midi_track.append(mido.Message(
                    "control_change", control=_MIDI_CC_PAN, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PITCH_BEND:
                pitch_val = self._cseq_bend_to_midi(event.pitch)
                midi_track.append(mido.Message(
                    "pitchwheel", pitch=pitch_val,
                    channel=channel, time=delta,
                ))

            elif event.event_type in (
                CseqEventType.END_TRACK,
                CseqEventType.END_TRACK_2,
                CseqEventType.TERMINATOR,
            ):
                midi_track.append(mido.MetaMessage("end_of_track", time=delta))
                break

        if not midi_track or not isinstance(midi_track[-1], mido.MetaMessage):
            midi_track.append(mido.MetaMessage("end_of_track", time=0))

        return midi_track

    def _cseq_bend_to_midi(self, cseq_value: int) -> int:
        return int(cseq_value / _CSEQ_MAX_PITCH_BEND * _MIDI_PITCH_BEND_RANGE) - _MIDI_PITCH_BEND_CENTER
