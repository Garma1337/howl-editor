# coding: utf-8

from dataclasses import dataclass, field, replace

from howl_editor.ctr.audio_settings import DEFAULT_DISTORT
from howl_editor.ctr.formats.cseq.models import CseqEventType, CseqFile, CseqSong
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ps1 import spu


@dataclass(frozen=True)
class PitchExceedance:
    """One instrument or percussion that asks the SPU for more speed than it has.

    `register` is the *un-truncated* value the note asks for, so an overflow is
    visible. `garbage` says which failure mode this is — for a reduced
    per-slot finding it is true when any note the slot plays wraps below the
    cap, even if the lowest offending note only caps flat."""

    slot: int
    is_drum: bool
    sample_id: int
    base_pitch: int
    note: int | None
    register: int
    garbage: bool = False

    @property
    def over_by(self) -> int:
        return self.register - spu.MAX_PITCH


@dataclass(frozen=True)
class PitchCeilingResult:
    exceedances: list[PitchExceedance] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.exceedances

    @property
    def worst(self) -> PitchExceedance | None:
        if not self.exceedances:
            return None

        return max(self.exceedances, key=lambda e: e.register)


class PitchCeilingValidator:
    """Finds notes the console cannot play as high as the song asks.

    Past the SPU's pitch ceiling the affected notes play flat and every note
    above them collapses onto the same pitch, taking the top of the melody out
    of tune, and nothing errors (see PitchCalculator for the register
    arithmetic and the 16-bit wrap). Only the notes a song actually plays are
    judged, since an instrument is free to be tuned so that notes it never
    reaches would overflow."""

    def __init__(self, pitch_calculator: PitchCalculator):
        self._pitch = pitch_calculator

    def validate(self, cseq: CseqFile) -> PitchCeilingResult:
        out: list[PitchExceedance] = []
        out.extend(self._check_instruments(cseq))
        out.extend(self._check_percussions(cseq))

        return PitchCeilingResult(exceedances=out)

    def _check_instruments(self, cseq: CseqFile) -> list[PitchExceedance]:
        out: list[PitchExceedance] = []

        for (patch, note, distort) in self._played_notes(cseq):
            if patch >= len(cseq.instruments):
                continue

            inst = cseq.instruments[patch]
            register = self._pitch.instrument_register_untruncated(
                inst.frequency, note, distort,
            )

            if register <= spu.MAX_PITCH:
                continue

            out.append(PitchExceedance(
                slot=patch,
                is_drum=False,
                sample_id=inst.sample_id,
                base_pitch=inst.frequency,
                note=note,
                register=register,
                garbage=self._pitch.instrument_plays_garbage(inst.frequency, note, distort),
            ))

        return self._lowest_per_slot(out)

    def _check_percussions(self, cseq: CseqFile) -> list[PitchExceedance]:
        """Percussion pitch is not transposed by the note, so its stored value
        is what the register gets — checkable without walking any track."""
        out: list[PitchExceedance] = []

        for slot, perc in enumerate(cseq.percussions):
            register = self._pitch.drum_register(perc.frequency, DEFAULT_DISTORT)

            if register <= spu.MAX_PITCH:
                continue

            out.append(PitchExceedance(
                slot=slot,
                is_drum=True,
                sample_id=perc.sample_id,
                base_pitch=perc.frequency,
                note=None,
                register=register,
            ))

        return out

    def _played_notes(self, cseq: CseqFile) -> set[tuple[int, int, int]]:
        """(patch, note, distort) for every melodic note the file triggers,
        across all of a CSEQ's sequences."""
        out: set[tuple[int, int, int]] = set()

        for song in cseq.songs:
            out |= self._song_notes(song)

        return out

    def _song_notes(self, song: CseqSong) -> set[tuple[int, int, int]]:
        out: set[tuple[int, int, int]] = set()

        for track in song.tracks:
            if track.is_drum:
                continue

            patch = 0
            distort = DEFAULT_DISTORT

            for event in track.events:
                if event.event_type == CseqEventType.CHANGE_PATCH:
                    patch = event.pitch
                elif event.event_type == CseqEventType.PITCH_BEND:
                    distort = event.pitch
                elif event.event_type == CseqEventType.NOTE_ON and event.velocity > 0:
                    out.add((patch, event.pitch, distort))

        return out

    def _lowest_per_slot(self, found: list[PitchExceedance]) -> list[PitchExceedance]:
        """One finding per instrument, at the lowest note that overflows —
        every note above it overflows too, so listing them all would bury the
        one number the user needs to bring back under the ceiling."""
        best: dict[int, PitchExceedance] = {}
        slot_garbage: dict[int, bool] = {}

        for item in found:
            slot_garbage[item.slot] = slot_garbage.get(item.slot, False) or item.garbage
            current = best.get(item.slot)

            if current is None or item.note < current.note:
                best[item.slot] = item

        return [
            replace(best[k], garbage=slot_garbage[k]) for k in sorted(best)
        ]
