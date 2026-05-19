# coding: utf-8

import io
from dataclasses import dataclass
from pathlib import Path

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import (
    CseqFile, CseqInstrument, CseqSong, CseqTrack, CseqEventType,
)
from howl_editor.midi import format as midi_fmt
from howl_editor.midi.mido_message_type import MidoMessageType

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False


@dataclass(frozen=True)
class MidiExportOptions:
    """Toggles that adjust what the MIDI exporter writes.

    `include_volume_events` — when True (default), mid-song VELOCITY changes
    are emitted as CC #7 volume changes so the DAW reproduces CTR's volume
    curves.

    `apply_instrument_volume` — when True, each track gets a CC #7 volume
    written at tick 0 based on the volume field of the instrument it's
    bound to.
    """
    include_volume_events: bool = True
    apply_instrument_volume: bool = False


_DEFAULT_OPTIONS = MidiExportOptions()


class CseqMidiExporter:

    def export(
        self, cseq: CseqFile, song_index: int = 0,
        options: MidiExportOptions = _DEFAULT_OPTIONS,
    ) -> bytes:
        if not HAS_MIDO:
            raise RuntimeError("mido is required for MIDI export")

        if song_index >= len(cseq.songs):
            raise ValueError(f"Song index {song_index} out of range (0..{len(cseq.songs) - 1})")

        mid = self._build_midi(cseq, song_index, options)
        buf = io.BytesIO()
        mid.save(file=buf)
        return buf.getvalue()

    def export_to_file(
        self, cseq: CseqFile, path: str | Path, song_index: int = 0,
        options: MidiExportOptions = _DEFAULT_OPTIONS,
    ) -> None:
        Path(path).write_bytes(self.export(cseq, song_index, options))

    def _build_midi(
        self, cseq: CseqFile, song_index: int, options: MidiExportOptions,
    ) -> 'mido.MidiFile':
        song = cseq.songs[song_index]
        mid = mido.MidiFile(type=1, ticks_per_beat=song.tpqn)

        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage(MidoMessageType.SET_TEMPO, tempo=mido.bpm2tempo(song.bpm), time=0))
        tempo_track.append(mido.MetaMessage(MidoMessageType.END_OF_TRACK, time=0))
        mid.tracks.append(tempo_track)

        next_channel = 0
        for track in song.tracks:
            channel, next_channel = self._assign_channel(track.is_drum, next_channel)
            midi_track = self._convert_track(track, channel, cseq.instruments, options)
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

    def _convert_track(
        self, track: CseqTrack, channel: int,
        instruments: list[CseqInstrument], options: MidiExportOptions,
    ) -> 'mido.MidiTrack':
        midi_track = mido.MidiTrack()

        if options.apply_instrument_volume:
            initial_vol = self._track_initial_volume(track, instruments)

            if initial_vol is not None:
                midi_track.append(mido.Message(
                    MidoMessageType.CONTROL_CHANGE, control=midi_fmt.CC_VOLUME,
                    value=initial_vol, channel=channel, time=0,
                ))

        # When include_volume_events is off we drop VELOCITY events, but the
        # CSEQ stores cumulative delta-times — the next emitted message has
        # to absorb the skipped tick count or following notes land too early.
        pending_delta = 0

        for event in track.events:
            delta = event.delta + pending_delta
            pending_delta = 0

            if event.event_type == CseqEventType.VELOCITY and not options.include_volume_events:
                pending_delta = delta
                continue

            msg = self._build_midi_message(event, channel, delta)
            if msg is None:
                pending_delta = delta
                continue

            midi_track.append(msg)

            if event.event_type in (
                CseqEventType.END_TRACK,
                CseqEventType.END_TRACK_2,
                CseqEventType.TERMINATOR,
            ):
                break

        if not midi_track or not isinstance(midi_track[-1], mido.MetaMessage):
            midi_track.append(mido.MetaMessage(
                MidoMessageType.END_OF_TRACK, time=pending_delta,
            ))

        return midi_track

    def _build_midi_message(
        self, event, channel: int, delta: int,
    ) -> 'mido.Message | mido.MetaMessage | None':
        et = event.event_type

        if et == CseqEventType.CHANGE_PATCH:
            return mido.Message(
                MidoMessageType.PROGRAM_CHANGE, program=event.pitch,
                channel=channel, time=delta,
            )

        if et == CseqEventType.NOTE_ON:
            return mido.Message(
                MidoMessageType.NOTE_ON, note=event.pitch, velocity=event.velocity,
                channel=channel, time=delta,
            )

        if et == CseqEventType.NOTE_OFF:
            return mido.Message(
                MidoMessageType.NOTE_OFF, note=event.pitch, velocity=0,
                channel=channel, time=delta,
            )

        if et == CseqEventType.VELOCITY:
            return mido.Message(
                MidoMessageType.CONTROL_CHANGE, control=midi_fmt.CC_VOLUME,
                value=event.pitch, channel=channel, time=delta,
            )

        if et == CseqEventType.PAN:
            return mido.Message(
                MidoMessageType.CONTROL_CHANGE, control=midi_fmt.CC_PAN,
                value=event.pitch, channel=channel, time=delta,
            )

        if et == CseqEventType.PITCH_BEND:
            return mido.Message(
                MidoMessageType.PITCHWHEEL,
                pitch=self._cseq_bend_to_midi(event.pitch),
                channel=channel, time=delta,
            )

        if et in (
            CseqEventType.END_TRACK,
            CseqEventType.END_TRACK_2,
            CseqEventType.TERMINATOR,
        ):
            return mido.MetaMessage(MidoMessageType.END_OF_TRACK, time=delta)

        return None

    def _track_initial_volume(
        self, track: CseqTrack, instruments: list[CseqInstrument],
    ) -> int | None:
        """Return a MIDI CC #7 volume (0-127) derived from the instrument
        bound to this track, or None when there's no resolvable instrument."""
        if track.is_drum:
            return None

        idx = track.instrument
        if idx < 0 or idx >= len(instruments):
            return None

        return int(instruments[idx].volume * midi_fmt.CC_MAX / cseq_fmt.CC_MAX)

    def _cseq_bend_to_midi(self, cseq_value: int) -> int:
        return int(cseq_value / cseq_fmt.MAX_PITCH_BEND * midi_fmt.PITCH_BEND_RANGE) - midi_fmt.PITCH_BEND_CENTER
