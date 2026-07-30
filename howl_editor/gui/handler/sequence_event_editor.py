# coding: utf-8

from howl_editor.ctr.formats.cseq.models import CseqEventType, CseqSong


class SequenceEventEditor:
    """The event-editing operations of one sequence, with its location in the
    file already bound in.

    TrackEventsDialog knows which track and event the user picked but nothing
    about which song or sequence it is showing. Binding those two indices here
    lets the dialog call these methods directly instead of going through
    per-call lambdas that have to repeat every parameter.

    The mutating methods return the re-read CseqSong so the dialog can refresh
    in place, or None when the edit failed or was declined.
    """

    def __init__(self, song_handler, song_index: int, seq_index: int):
        self._handler = song_handler
        self._song_index = song_index
        self._seq_index = seq_index

    def edit_event(
        self, track_index: int, event_index: int,
        pitch: int, velocity: int, delta: int,
    ) -> CseqSong | None:
        return self._handler.edit_track_event(
            self._song_index, self._seq_index, track_index, event_index,
            pitch, velocity, delta,
        )

    def insert_event(
        self, track_index: int, event_index: int, event_type: CseqEventType,
        pitch: int, velocity: int, delta: int,
    ) -> CseqSong | None:
        return self._handler.insert_track_event(
            self._song_index, self._seq_index, track_index, event_index,
            event_type, pitch, velocity, delta,
        )

    def delete_event(self, track_index: int, event_index: int) -> CseqSong | None:
        return self._handler.delete_track_event(
            self._song_index, self._seq_index, track_index, event_index,
        )

    def replace_track_from_midi(self, track_index: int) -> None:
        """Unlike the others this reloads the whole Workshop rather than
        refreshing the open dialog, so it returns nothing."""
        self._handler.replace_track_from_midi(
            self._song_index, self._seq_index, track_index,
        )
