# coding: utf-8

from pathlib import Path

import pytest

from howl_editor.core.vlq import VlqCodec
from howl_editor.ctr.analysis.stock_name_resolver import StockNameResolver
from howl_editor.ctr.formats.cseq.models import CseqEventType
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.cseq.writer import CseqWriter
from howl_editor.midi.converter import MidiConverter
from howl_editor.midi.drum_pitch_remapper import DrumPitchRemapper
from howl_editor.midi.models import (
    MidiConvertSettings, InstrumentMapping, DrumPitchMapping,
)

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

pytestmark = pytest.mark.skipif(not HAS_MIDO, reason="mido not installed")


def _converter():
    vlq = VlqCodec()
    return MidiConverter(CseqWriter(vlq), DrumPitchRemapper())


def _reader():
    return CseqReader(VlqCodec(), StockNameResolver())


def _create_midi(tmp_path: Path, bpm: int = 120, notes: list[tuple[int, int, int]] | None = None) -> Path:
    """Create a simple MIDI file with optional notes as (pitch, velocity, duration_ticks)."""
    mid = mido.MidiFile(type=1, ticks_per_beat=480)

    tempo_track = mido.MidiTrack()
    tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    tempo_track.append(mido.MetaMessage("end_of_track", time=0))
    mid.tracks.append(tempo_track)

    if notes:
        note_track = mido.MidiTrack()

        for pitch, vel, dur in notes:
            note_track.append(mido.Message("note_on", note=pitch, velocity=vel, time=0))
            note_track.append(mido.Message("note_off", note=pitch, velocity=0, time=dur))

        note_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(note_track)

    path = tmp_path / "test.mid"
    mid.save(str(path))
    return path


class TestGetMidiInfo:

    def test_reads_basic_info(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, bpm=140, notes=[(60, 100, 480)])
        info = conv.get_midi_info(path)

        assert info.midi_type == 1
        assert info.ticks_per_beat == 480
        assert info.num_tracks == 2

    def test_track_info(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, notes=[(60, 100, 480), (64, 80, 240)])
        info = conv.get_midi_info(path)
        note_track = info.tracks[1]

        assert note_track.note_count == 2

    def test_all_pitches_captured_for_non_drum_channel(self, tmp_path):
        # Notes on channel 0 are not GM drums, so drum_pitches stays empty but
        # all_pitches still lists them — that's the pitch set the dialog's
        # manual Drum toggle expands into percussion slots.
        conv = _converter()
        path = _create_midi(tmp_path, notes=[(64, 100, 240), (60, 100, 240), (64, 80, 240)])
        note_track = conv.get_midi_info(path).tracks[1]

        assert note_track.drum_pitches == []
        assert note_track.all_pitches == [60, 64]


class TestConvert:

    def test_produces_valid_cseq(self, tmp_path):
        conv = _converter()
        reader = _reader()
        path = _create_midi(tmp_path, notes=[(60, 100, 480)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0, frequency=0x1000)],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.songs) == 1
        assert len(cseq.songs[0].tracks) >= 1

    def test_drum_track(self, tmp_path):
        conv = _converter()
        reader = _reader()
        path = _create_midi(tmp_path, notes=[(36, 100, 120)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(is_drum=True, sample_id=0)],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.percussions) == 1

    def test_extracts_tempo(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, bpm=150, notes=[(60, 100, 480)])

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)

        assert cseq.songs[0].bpm == 150

    def test_no_notes_produces_empty_tracks(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path)
        settings = MidiConvertSettings()
        cseq = conv.convert_to_model(path, settings)

        assert len(cseq.songs[0].tracks) == 0

    def test_cc_volume_scaled_from_7bit_to_8bit(self, tmp_path):
        """CTR expects 0-255 for VELOCITY events; MIDI CC#7 is 0-127. The full
        MIDI range must hit the full CSEQ range or songs come out half-volume."""
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        cc_track = mido.MidiTrack()
        cc_track.append(mido.Message("control_change", control=7, value=127, time=0))
        cc_track.append(mido.Message("control_change", control=7, value=0, time=10))
        cc_track.append(mido.Message("control_change", control=7, value=64, time=10))
        cc_track.append(mido.Message("note_on", note=60, velocity=100, time=10))
        cc_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        cc_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(cc_track)
        path = tmp_path / "vol.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )
        cseq = conv.convert_to_model(path, settings)
        velocity_events = [
            e for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.VELOCITY
        ]

        assert [e.pitch for e in velocity_events] == [255, 0, 128]

    def test_cc_pan_scaled_from_7bit_to_8bit(self, tmp_path):
        """CC#10 (pan) likewise expands from 0-127 to 0-255."""
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        cc_track = mido.MidiTrack()
        cc_track.append(mido.Message("control_change", control=10, value=127, time=0))
        cc_track.append(mido.Message("note_on", note=60, velocity=100, time=10))
        cc_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        cc_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(cc_track)
        path = tmp_path / "pan.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )
        cseq = conv.convert_to_model(path, settings)
        pan_events = [
            e for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.PAN
        ]

        assert pan_events and pan_events[0].pitch == 255

    def test_drum_track_creates_one_percussion_per_unique_pitch(self, tmp_path):
        """MIDI drum tracks usually have many GM pitches (36 kick, 38 snare,
        42 hi-hat). Each needs its own CseqPercussion slot — CTR-tools does
        the same in HowlControl.cs ImportMIDI."""
        conv = _converter()
        reader = _reader()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (36, 38, 42, 36, 38):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "drums.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[
                InstrumentMapping(),
                InstrumentMapping(is_drum=True, drum_pitches=[
                    DrumPitchMapping(midi_pitch=36, sample_id=10),
                    DrumPitchMapping(midi_pitch=38, sample_id=11),
                    DrumPitchMapping(midi_pitch=42, sample_id=12),
                ]),
            ],
        )

        cseq_bytes = conv.convert(path, settings)
        cseq = reader.read(cseq_bytes)

        assert len(cseq.percussions) == 3
        assert [p.sample_id for p in cseq.percussions] == [10, 11, 12]

    def test_drum_track_remaps_note_pitches_to_percussion_indices(self, tmp_path):
        """The on-disk NOTE_ON pitch must be 0, 1, 2... (Percussions[] index),
        not the original MIDI note number — otherwise the game reads past the
        percussion table."""
        conv = _converter()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (38, 36, 42):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "remap.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[
                InstrumentMapping(),
                InstrumentMapping(is_drum=True, drum_pitches=[
                    DrumPitchMapping(midi_pitch=36, sample_id=0),
                    DrumPitchMapping(midi_pitch=38, sample_id=1),
                    DrumPitchMapping(midi_pitch=42, sample_id=2),
                ]),
            ],
        )

        cseq = conv.convert_to_model(path, settings)
        drum_cseq_track = cseq.songs[0].tracks[0]
        note_on_pitches = [
            e.pitch for e in drum_cseq_track.events
            if e.event_type == CseqEventType.NOTE_ON
        ]

        # MIDI order was 38, 36, 42 — the user's table order was 36, 38, 42 →
        # remap indices: 1, 0, 2.
        assert note_on_pitches == [1, 0, 2]

    def test_separate_drum_tracks_share_one_global_percussion_table(self, tmp_path):
        """The user's CTR-tools layout: one percussion instrument per MIDI
        track, each on a single note, all on channel 10. A drum NOTE pitch is
        a direct index into Percussions[] with no per-track base, so every
        track must resolve against ONE shared table. Track 0's kick → slot 0,
        track 1's snare → slot 1 — they must NOT both collapse to slot 0."""
        conv = _converter()
        reader = _reader()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        # Three separate drum tracks, one note each, all on channel 9 (GM 10).
        for pitch in (36, 38, 42):
            t = mido.MidiTrack()
            t.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            t.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
            t.append(mido.MetaMessage("end_of_track", time=0))
            mid.tracks.append(t)

        path = tmp_path / "multi_drum.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[
                InstrumentMapping(),  # tempo track
                InstrumentMapping(is_drum=True, drum_pitches=[DrumPitchMapping(midi_pitch=36, sample_id=10)]),
                InstrumentMapping(is_drum=True, drum_pitches=[DrumPitchMapping(midi_pitch=38, sample_id=11)]),
                InstrumentMapping(is_drum=True, drum_pitches=[DrumPitchMapping(midi_pitch=42, sample_id=12)]),
            ],
        )

        cseq = reader.read(conv.convert(path, settings))

        # One shared percussion table, one slot per distinct pitch.
        assert [p.sample_id for p in cseq.percussions] == [10, 11, 12]

        # Each track's single note points at its OWN global slot, not slot 0.
        note_pitches = [
            [e.pitch for e in t.events if e.event_type == CseqEventType.NOTE_ON]
            for t in cseq.songs[0].tracks
        ]
        assert note_pitches == [[0], [1], [2]]

    def test_drum_tracks_carry_no_change_patch(self, tmp_path):
        conv = _converter()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        drum_track.append(mido.Message("note_on", channel=9, note=36, velocity=100, time=0))
        drum_track.append(mido.Message("note_off", channel=9, note=36, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "drum_nopatch.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(is_drum=True, sample_id=0)],
        )
        cseq = conv.convert_to_model(path, settings)
        drum_cseq_track = cseq.songs[0].tracks[0]

        assert all(e.event_type != CseqEventType.CHANGE_PATCH for e in drum_cseq_track.events)

    def test_melodic_track_pitches_pass_through_unchanged(self, tmp_path):
        conv = _converter()
        path = _create_midi(tmp_path, notes=[(60, 100, 240), (64, 90, 240)])
        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)
        notes = [
            e.pitch for t in cseq.songs[0].tracks for e in t.events
            if e.event_type == CseqEventType.NOTE_ON
        ]

        assert notes == [60, 64]

    def test_get_midi_info_reports_drum_pitches(self, tmp_path):
        conv = _converter()

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        drum_track = mido.MidiTrack()
        for pitch in (42, 36, 38, 36):
            drum_track.append(mido.Message("note_on", channel=9, note=pitch, velocity=100, time=0))
            drum_track.append(mido.Message("note_off", channel=9, note=pitch, velocity=0, time=60))
        drum_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(drum_track)

        path = tmp_path / "info.mid"
        mid.save(str(path))

        info = conv.get_midi_info(path)

        assert info.tracks[1].drum_pitches == [36, 38, 42]
        assert info.tracks[0].drum_pitches == []

    def test_pitch_bend_conversion(self, tmp_path):
        conv = _converter()
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        tempo_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(tempo_track)

        note_track = mido.MidiTrack()
        note_track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        note_track.append(mido.Message("pitchwheel", pitch=0, time=100))
        note_track.append(mido.Message("note_off", note=60, velocity=0, time=100))
        note_track.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(note_track)

        path = tmp_path / "bend.mid"
        mid.save(str(path))

        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )

        cseq = conv.convert_to_model(path, settings)
        bend_events = [e for t in cseq.songs[0].tracks for e in t.events if e.event_type == CseqEventType.PITCH_BEND]

        assert len(bend_events) == 1
        assert 0 <= bend_events[0].pitch <= 255


class TestExtractTrackEvents:

    def test_brackets_with_change_patch_and_end_track(self, tmp_path):
        path = _create_midi(tmp_path, notes=[(60, 100, 240)])
        events = _converter().extract_track_events(path, 1, instrument_index=7)

        assert events[0].event_type == CseqEventType.CHANGE_PATCH
        assert events[0].pitch == 7
        assert events[-1].event_type == CseqEventType.END_TRACK

    def test_translates_note_on_and_note_off(self, tmp_path):
        path = _create_midi(tmp_path, notes=[(60, 100, 240)])
        events = _converter().extract_track_events(path, 1, instrument_index=0)

        types = [e.event_type for e in events]
        assert CseqEventType.NOTE_ON in types
        assert CseqEventType.NOTE_OFF in types

    def test_preserves_velocity_on_note_on(self, tmp_path):
        path = _create_midi(tmp_path, notes=[(60, 99, 240)])
        events = _converter().extract_track_events(path, 1, instrument_index=0)
        note_ons = [e for e in events if e.event_type == CseqEventType.NOTE_ON]

        assert note_ons[0].velocity == 99

    def test_out_of_range_track_raises(self, tmp_path):
        path = _create_midi(tmp_path, notes=[(60, 100, 240)])

        with pytest.raises(IndexError):
            _converter().extract_track_events(path, 9, instrument_index=0)

    def test_includes_meta_only_tracks_without_notes(self, tmp_path):
        # The tempo track (index 0) has no notes — extraction shouldn't crash,
        # it just produces a minimal CHANGE_PATCH + END_TRACK.
        path = _create_midi(tmp_path)
        events = _converter().extract_track_events(path, 0, instrument_index=0)

        assert events[0].event_type == CseqEventType.CHANGE_PATCH
        assert events[-1].event_type == CseqEventType.END_TRACK


def _mask_song(bpm, num_tracks):
    """A stand-in mask sequence: `num_tracks` tracks, each with a handful of
    note events, matching the shape of an Aku Aku / Uka Uka mask sub-song."""
    from howl_editor.ctr.formats.cseq.models import CseqSong, CseqTrack, CseqEvent

    tracks = []
    for t in range(num_tracks):
        events = [CseqEvent(delta=0, event_type=CseqEventType.CHANGE_PATCH, pitch=t)]
        for n in range(4):
            events.append(CseqEvent(delta=48, event_type=CseqEventType.NOTE_ON, pitch=60 + n, velocity=90))
            events.append(CseqEvent(delta=24, event_type=CseqEventType.NOTE_OFF, pitch=60 + n))
        events.append(CseqEvent(delta=0, event_type=CseqEventType.END_TRACK))
        tracks.append(CseqTrack(flags=0, events=events, instrument=t))

    return CseqSong(bpm=bpm, tpqn=480, tracks=tracks)


class TestMidiIntoMaskSequence:
    """The user's scenario: a race-track song (0-27) holds three sub-songs —
    main music + Aku Aku + Uka Uka masks. Importing a MIDI into the main
    sequence must leave the two masks untouched."""

    def test_replacing_main_sequence_preserves_masks(self, tmp_path):
        from howl_editor.ctr.formats.cseq.editor import CseqEditor
        from howl_editor.ctr.formats.cseq.models import CseqFile

        vlq = VlqCodec()
        writer = CseqWriter(vlq)
        reader = _reader()
        editor = CseqEditor(reader, writer)

        original = CseqFile(songs=[_mask_song(120, 8), _mask_song(130, 3), _mask_song(140, 3)])
        blob = writer.serialize(original)

        # Convert a MIDI and graft its single sub-song into sequence 0.
        path = _create_midi(tmp_path, bpm=100, notes=[(60, 100, 240), (64, 90, 240)])
        settings = MidiConvertSettings(
            mappings=[InstrumentMapping(), InstrumentMapping(sample_id=0)],
        )
        imported = _converter().convert_to_model(path, settings)

        new_blob = editor.replace_sequence(blob, 0, imported.songs[0])
        parsed = reader.read(new_blob)

        # Still three sequences, and the two masks are byte-for-byte intact.
        assert len(parsed.songs) == 3
        assert parsed.songs[0].bpm == 100
        assert [len(t.events) for t in parsed.songs[1].tracks] == [len(t.events) for t in original.songs[1].tracks]
        assert [len(t.events) for t in parsed.songs[2].tracks] == [len(t.events) for t in original.songs[2].tracks]
