# coding: utf-8

from howl_editor.models import (
    CseqInstrument, CseqPercussion, CseqTrack, CseqEventType, CseqInfo,
    CSEQ_EVENT_PARAMS, CSEQ_TERMINAL_EVENTS,
)


class TestCseqInstrument:
    def test_freq_hz_default(self):
        inst = CseqInstrument()
        assert inst.freq_hz == int(0x1000 / 4096 * 44100)

    def test_freq_hz_setter(self):
        inst = CseqInstrument()
        inst.freq_hz = 22050
        assert inst.frequency == int(22050 * 4096 / 44100)

    def test_defaults(self):
        inst = CseqInstrument()
        assert inst.flags == 1
        assert inst.volume == 255
        assert inst.adsr == 0x1FC180FF


class TestCseqPercussion:
    def test_freq_hz(self):
        perc = CseqPercussion(frequency=2048)
        assert perc.freq_hz == int(2048 / 4096 * 44100)


class TestCseqTrack:
    def test_is_drum_when_flag_set(self):
        track = CseqTrack(flags=1)
        assert track.is_drum is True

    def test_not_drum_when_flag_clear(self):
        track = CseqTrack(flags=0)
        assert track.is_drum is False

    def test_is_drum_checks_bit_0(self):
        track = CseqTrack(flags=3)
        assert track.is_drum is True

    def test_defaults(self):
        track = CseqTrack()
        assert track.flags == 0
        assert track.unk == 0
        assert track.instrument == 0
        assert track.is_drum is False


class TestCseqEventParams:
    def test_note_on_has_two_params(self):
        assert CSEQ_EVENT_PARAMS[CseqEventType.NOTE_ON] == 2

    def test_end_track_has_zero_params(self):
        assert CSEQ_EVENT_PARAMS[CseqEventType.END_TRACK] == 0

    def test_note_off_has_one_param(self):
        assert CSEQ_EVENT_PARAMS[CseqEventType.NOTE_OFF] == 1


class TestCseqTerminalEvents:
    def test_end_track_is_terminal(self):
        assert CseqEventType.END_TRACK in CSEQ_TERMINAL_EVENTS

    def test_note_on_is_not_terminal(self):
        assert CseqEventType.NOTE_ON not in CSEQ_TERMINAL_EVENTS


class TestCseqInfo:
    def test_defaults(self):
        info = CseqInfo()
        assert info.file_size == 0
        assert info.num_instruments == 0
        assert info.num_percussions == 0
        assert info.num_songs == 0
