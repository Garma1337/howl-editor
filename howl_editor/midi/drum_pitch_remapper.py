# coding: utf-8


from howl_editor.midi import format as midi_fmt


class DrumPitchRemapper:
    """Maps MIDI drum pitches to CSEQ percussion indices.

    In CSEQ, a drum track's NOTE_ON / NOTE_OFF pitch byte is an index into the
    parent CSEQ's Percussions[] array, not a MIDI note number. Forwarding the
    raw MIDI pitch (e.g. 36 = kick) would point past the percussion table and
    play nothing.
    """

    def collect_drum_pitches(self, midi_track) -> list[int]:
        """Return sorted unique note pitches found on the GM drum channel in
        this MIDI track. Empty if the track has no drum-channel notes."""
        pitches: set[int] = set()

        for msg in midi_track:
            if not self._is_drum_note(msg):
                continue

            pitches.add(msg.note)

        return sorted(pitches)

    def collect_all_note_pitches(self, midi_track) -> list[int]:
        """Return sorted unique note pitches regardless of MIDI channel.

        Used as a fallback when the user has manually marked a track as drum
        even though it isn't on channel 9 — we still need a pitch table to
        size the percussion slots."""
        pitches: set[int] = set()

        for msg in midi_track:
            if msg.type in ("note_on", "note_off") and hasattr(msg, "note"):
                pitches.add(msg.note)

        return sorted(pitches)

    def remap(self, midi_pitch: int, pitch_table: list[int]) -> int:
        """Translate a MIDI drum pitch to its CSEQ percussion index. Raises
        ValueError if the pitch was never collected — callers should always
        build the table from the same track they later remap against."""
        return pitch_table.index(midi_pitch)

    def _is_drum_note(self, msg) -> bool:
        if msg.type not in ("note_on", "note_off"):
            return False

        if not hasattr(msg, "channel") or not hasattr(msg, "note"):
            return False

        return msg.channel == midi_fmt.DRUM_CHANNEL_INDEX
