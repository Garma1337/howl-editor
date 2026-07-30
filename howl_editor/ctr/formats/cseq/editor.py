# coding: utf-8

from howl_editor.ctr.formats.cseq import format as cseq_fmt
from howl_editor.ctr.formats.cseq.models import (
    CSEQ_EDITABLE_EVENTS, CseqEvent, CseqEventType, CseqInstrument,
    CseqPercussion, CseqSong, CseqTrack,
)
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

    def append_instrument(
        self, song_data: bytes, sample_id: int, volume: int, frequency: int,
        adsr: int | None = None,
    ) -> bytes:
        """Add a melodic instrument descriptor and return the new blob.

        The bank keeps one BankSample and one SPU upload; only the 12-byte
        descriptor is duplicated."""
        cseq = self._reader.read(song_data)
        instrument = CseqInstrument(
            flags=1,
            volume=max(0, min(cseq_fmt.MAX_VOLUME, volume)),
            frequency=max(0, min(cseq_fmt.MAX_PITCH_REGISTER, frequency)),
            sample_id=sample_id,
        )

        if adsr is not None:
            instrument.adsr = max(0, min(cseq_fmt.MAX_ADSR_REGISTER, adsr))

        cseq.instruments.append(instrument)

        return self._writer.serialize(cseq)

    def append_percussion(
        self, song_data: bytes, sample_id: int, volume: int, frequency: int,
    ) -> bytes:
        """Add a percussion descriptor and return the new blob."""
        cseq = self._reader.read(song_data)
        cseq.percussions.append(CseqPercussion(
            flags=1,
            volume=max(0, min(cseq_fmt.MAX_VOLUME, volume)),
            frequency=max(0, min(cseq_fmt.MAX_PITCH_REGISTER, frequency)),
            sample_id=sample_id,
        ))

        return self._writer.serialize(cseq)

    def update_event(
        self, song_data: bytes, seq_index: int, track_index: int,
        event_index: int, pitch: int, velocity: int | None = None,
        delta: int | None = None,
    ) -> bytes:
        """Change one event's parameter bytes (and optionally its delta).

        `pitch` is the first parameter byte whatever the opcode calls it — the
        bend amount for PITCH_BEND, the instrument index for CHANGE_PATCH, the
        percussion index for a drum NOTE_ON. `velocity` only applies to
        NOTE_ON, the sole two-parameter opcode; it is ignored otherwise."""
        cseq = self._reader.read(song_data)
        event = self._locate_editable_event(cseq, seq_index, track_index, event_index)

        event.pitch = max(0, min(cseq_fmt.CC_MAX, pitch))

        if velocity is not None and event.event_type == CseqEventType.NOTE_ON:
            event.velocity = max(0, min(cseq_fmt.CC_MAX, velocity))

        if delta is not None:
            event.delta = max(0, delta)

        return self._writer.serialize(cseq)

    def insert_event(
        self, song_data: bytes, seq_index: int, track_index: int,
        event_index: int, event_type: CseqEventType, pitch: int,
        velocity: int = 0, delta: int = 0,
    ) -> bytes:
        """Insert an event before event_index.

        The inserted event carries its own delta, so the event it displaces
        keeps its original delta and everything after it stays where it was —
        inserting with delta=0 leaves downstream timing untouched.

        Inserting a NOTE_ON does NOT synthesise its NOTE_OFF; a note left
        unterminated sustains until the track ends."""
        cseq = self._reader.read(song_data)

        if event_type not in CSEQ_EDITABLE_EVENTS:
            raise ValueError(f"{event_type.name} is not an insertable event")

        track = self._locate_track(cseq, seq_index, track_index)

        if event_index < 0 or event_index > len(track.events):
            raise IndexError(f"Event index {event_index} out of range")

        track.events.insert(event_index, CseqEvent(
            delta=max(0, delta),
            event_type=event_type,
            pitch=max(0, min(cseq_fmt.CC_MAX, pitch)),
            velocity=max(0, min(cseq_fmt.CC_MAX, velocity)),
        ))

        return self._writer.serialize(cseq)

    def delete_event(
        self, song_data: bytes, seq_index: int, track_index: int, event_index: int,
    ) -> bytes:
        """Remove one event, folding its delta into the event that follows so
        nothing downstream shifts earlier in time."""
        cseq = self._reader.read(song_data)
        track = self._locate_track(cseq, seq_index, track_index)
        event = self._locate_editable_event(cseq, seq_index, track_index, event_index)

        if event_index + 1 < len(track.events):
            track.events[event_index + 1].delta += event.delta

        del track.events[event_index]
        return self._writer.serialize(cseq)

    def _locate_editable_event(
        self, cseq, seq_index: int, track_index: int, event_index: int,
    ) -> CseqEvent:
        event = self._locate_event(cseq, seq_index, track_index, event_index)

        if event.event_type not in CSEQ_EDITABLE_EVENTS:
            raise ValueError(
                f"Event {event_index} is {event.event_type.name}, which the "
                f"event editor does not touch (it defines track structure)",
            )

        return event

    def _locate_track(self, cseq, seq_index: int, track_index: int) -> CseqTrack:
        if seq_index < 0 or seq_index >= len(cseq.songs):
            raise IndexError(f"Sequence index {seq_index} out of range")

        song = cseq.songs[seq_index]

        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError(f"Track index {track_index} out of range")

        return song.tracks[track_index]

    def _locate_event(
        self, cseq, seq_index: int, track_index: int, event_index: int,
    ) -> CseqEvent:
        track = self._locate_track(cseq, seq_index, track_index)

        if event_index < 0 or event_index >= len(track.events):
            raise IndexError(f"Event index {event_index} out of range")

        return track.events[event_index]

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
