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


class CseqMidiExporter:

    def export(self, cseq: CseqFile, song_index: int = 0) -> bytes:
        if not HAS_MIDO:
            raise RuntimeError("mido is required for MIDI export")

        if song_index >= len(cseq.songs):
            raise ValueError(f"Song index {song_index} out of range (0..{len(cseq.songs) - 1})")

        mid = self._build_midi(cseq, cseq.songs[song_index])
        buf = io.BytesIO()
        mid.save(file=buf)
        return buf.getvalue()

    def export_to_file(self, cseq: CseqFile, path: str | Path, song_index: int = 0) -> None:
        Path(path).write_bytes(self.export(cseq, song_index))

    def _build_midi(self, cseq: CseqFile, song: CseqSong) -> 'mido.MidiFile':
        mid = mido.MidiFile(type=1, ticks_per_beat=song.tpqn)

        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(song.bpm), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        next_channel = 0
        for track in song.tracks:
            if track.is_drum:
                channel = _DRUM_CHANNEL
            else:
                channel = next_channel
                if next_channel == _DRUM_CHANNEL:
                    next_channel += 1
                next_channel += 1
                if next_channel > 15:
                    next_channel = 0

            midi_track = self._convert_track(track, channel)
            mid.tracks.append(midi_track)

        return mid

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
                    "control_change", control=7, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PAN:
                midi_track.append(mido.Message(
                    "control_change", control=10, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PITCH_BEND:
                pitch_val = int(event.pitch / 255 * 16383) - 8192
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
