# coding: utf-8

import io
from pathlib import Path

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import CseqFile, CseqSong, CseqTrack, CseqEventType
from howl_editor.midi import format as midi_fmt
from howl_editor.midi.mido_message_type import MidoMessageType

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False


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
        tempo_track.append(mido.MetaMessage(MidoMessageType.SET_TEMPO, tempo=mido.bpm2tempo(song.bpm), time=0))
        tempo_track.append(mido.MetaMessage(MidoMessageType.END_OF_TRACK, time=0))
        mid.tracks.append(tempo_track)

        next_channel = 0
        for track in song.tracks:
            channel, next_channel = self._assign_channel(track.is_drum, next_channel)
            midi_track = self._convert_track(track, channel)
            mid.tracks.append(midi_track)

        return mid

    def _assign_channel(self, is_drum: bool, next_channel: int) -> tuple[int, int]:
        if is_drum:
            return midi_fmt.DRUM_CHANNEL_INDEX, next_channel

        channel = next_channel

        if next_channel == midi_fmt.DRUM_CHANNEL_INDEX:
            next_channel += 1

        next_channel += 1

        if next_channel > midi_fmt.MAX_CHANNEL_INDEX:
            next_channel = 0

        return channel, next_channel

    def _convert_track(self, track: CseqTrack, channel: int) -> 'mido.MidiTrack':
        midi_track = mido.MidiTrack()

        for event in track.events:
            delta = event.delta

            if event.event_type == CseqEventType.CHANGE_PATCH:
                midi_track.append(mido.Message(
                    MidoMessageType.PROGRAM_CHANGE, program=event.pitch, channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.NOTE_ON:
                midi_track.append(mido.Message(
                    MidoMessageType.NOTE_ON, note=event.pitch, velocity=event.velocity,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.NOTE_OFF:
                midi_track.append(mido.Message(
                    MidoMessageType.NOTE_OFF, note=event.pitch, velocity=0,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.VELOCITY:
                midi_track.append(mido.Message(
                    MidoMessageType.CONTROL_CHANGE, control=midi_fmt.CC_VOLUME, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PAN:
                midi_track.append(mido.Message(
                    MidoMessageType.CONTROL_CHANGE, control=midi_fmt.CC_PAN, value=event.pitch,
                    channel=channel, time=delta,
                ))

            elif event.event_type == CseqEventType.PITCH_BEND:
                pitch_val = self._cseq_bend_to_midi(event.pitch)
                midi_track.append(mido.Message(
                    MidoMessageType.PITCHWHEEL, pitch=pitch_val,
                    channel=channel, time=delta,
                ))

            elif event.event_type in (
                CseqEventType.END_TRACK,
                CseqEventType.END_TRACK_2,
                CseqEventType.TERMINATOR,
            ):
                midi_track.append(mido.MetaMessage(MidoMessageType.END_OF_TRACK, time=delta))
                break

        if not midi_track or not isinstance(midi_track[-1], mido.MetaMessage):
            midi_track.append(mido.MetaMessage(MidoMessageType.END_OF_TRACK, time=0))

        return midi_track

    def _cseq_bend_to_midi(self, cseq_value: int) -> int:
        return int(cseq_value / cseq_fmt.MAX_PITCH_BEND * midi_fmt.PITCH_BEND_RANGE) - midi_fmt.PITCH_BEND_CENTER
