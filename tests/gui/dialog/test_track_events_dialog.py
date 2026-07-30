# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog

from howl_editor.ctr.formats.cseq.models import (
    CseqEvent, CseqEventType, CseqSong, CseqTrack,
)
from howl_editor.gui.dialog import track_events_dialog
from howl_editor.gui.dialog.edit_event_dialog import EventEditResult
from howl_editor.gui.dialog.track_events_dialog import TrackEventsDialog


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def _song(*events: CseqEvent, is_drum: bool = False) -> CseqSong:
    track = CseqTrack(
        flags=1 if is_drum else 0,
        events=[*events, CseqEvent(event_type=CseqEventType.END_TRACK)],
    )

    return CseqSong(bpm=120, tpqn=480, tracks=[track])


class _RecordingEditor:
    """Stands in for SequenceEventEditor. Records what the dialog asked for
    and returns `result` so _apply can be exercised."""

    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def edit_event(self, *args):
        self.calls.append(("edit_event", args))
        return self.result

    def insert_event(self, *args):
        self.calls.append(("insert_event", args))
        return self.result

    def delete_event(self, *args):
        self.calls.append(("delete_event", args))
        return self.result

    def replace_track_from_midi(self, *args):
        self.calls.append(("replace_track_from_midi", args))
        return None


def _param_columns(dialog: TrackEventsDialog, row: int) -> tuple[str, str]:
    return (
        dialog._event_table.item(row, 2).text(),
        dialog._event_table.item(row, 3).text(),
    )


class TestModulationParamDisplay:
    """The reader stores a single-parameter event's byte in `pitch` and only
    fills `velocity` for two-parameter NOTE_ON. Reading `velocity` for the
    modulation events made every one of them render as a flat 0."""

    @pytest.mark.parametrize(("event_type", "expected"), [
        (CseqEventType.VELOCITY, "vol=200"),
        (CseqEventType.PAN, "pan=200"),
        (CseqEventType.REVERB, "reverb=200"),
        (CseqEventType.PITCH_BEND, "bend=200"),
        (CseqEventType.CHANGE_PATCH, "patch=200"),
    ])
    def test_shows_the_actual_parameter_byte(self, qt_app, event_type, expected):
        dialog = TrackEventsDialog(
            None, "t", _song(CseqEvent(delta=0, event_type=event_type, pitch=200)),
        )

        assert _param_columns(dialog, 0)[0] == expected

    def test_note_on_shows_both_params(self, qt_app):
        dialog = TrackEventsDialog(None, "t", _song(
            CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=60, velocity=99),
        ))

        assert _param_columns(dialog, 0) == ("pitch=60", "vel=99")

    def test_pitch_bend_hint_reads_as_semitones(self, qt_app):
        dialog = TrackEventsDialog(None, "t", _song(
            CseqEvent(delta=0, event_type=CseqEventType.PITCH_BEND, pitch=0x80),
        ))

        assert _param_columns(dialog, 0)[1] == "no bend (neutral)"

    def test_pitch_bend_hint_signs_the_offset(self, qt_app):
        dialog = TrackEventsDialog(None, "t", _song(
            CseqEvent(delta=0, event_type=CseqEventType.PITCH_BEND, pitch=0xC0),
        ))

        assert _param_columns(dialog, 0)[1] == "+1.00 semitones"


class TestEditingAffordances:

    def test_editing_controls_absent_without_callbacks(self, qt_app):
        dialog = TrackEventsDialog(None, "t", _song(
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64),
        ))

        assert not dialog._editing_enabled()
        assert not hasattr(dialog, "_edit_event_btn")

    def test_edit_enabled_for_editable_event(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64)),
            editor=_RecordingEditor(),
        )
        dialog._event_table.selectRow(0)

        assert dialog._edit_event_btn.isEnabled()
        assert dialog._delete_event_btn.isEnabled()

    def test_edit_disabled_on_terminal_event(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t", _song(),
            editor=_RecordingEditor(),
        )
        # Row 0 is the END_TRACK the fixture appends.
        dialog._event_table.selectRow(0)

        assert not dialog._edit_event_btn.isEnabled()
        assert not dialog._delete_event_btn.isEnabled()

    def test_drum_track_is_detected(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t",
            _song(
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=13, velocity=99),
                is_drum=True,
            ),
            editor=_RecordingEditor(),
            percussion_count=16,
        )
        dialog._track_list.setCurrentRow(0)

        assert dialog._current_track_is_drum()
        assert dialog._descriptor_count_for_current_track() == 16


class _StubEventDialog:
    """Stands in for EditEventDialog so the mutation paths can be driven
    without a modal exec(). `result` is what chosen() hands back."""

    accepted = True
    result = None
    last_kwargs = None

    def __init__(self, *args, **kwargs):
        type(self).last_kwargs = kwargs
        self._args = args

    def exec(self):
        return QDialog.Accepted if type(self).accepted else QDialog.Rejected

    def chosen(self):
        return type(self).result


@pytest.fixture
def stub_dialog(monkeypatch):
    _StubEventDialog.accepted = True
    _StubEventDialog.result = None
    _StubEventDialog.last_kwargs = None
    monkeypatch.setattr(track_events_dialog, "EditEventDialog", _StubEventDialog)
    return _StubEventDialog


def _result(event_type, pitch, velocity=0, delta=0):
    return EventEditResult(
        event_type=event_type, pitch=pitch, velocity=velocity, delta=delta,
    )


class TestMutationCallbacks:

    def test_edit_forwards_chosen_values(self, qt_app, stub_dialog):
        editor = _RecordingEditor()
        stub_dialog.result = _result(CseqEventType.PITCH_BEND, 200, 0, 3)

        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PITCH_BEND, pitch=128)),
            editor=editor,
        )
        dialog._event_table.selectRow(0)
        dialog._do_edit_event()

        assert editor.calls == [("edit_event", (0, 0, 200, 0, 3))]

    def test_insert_forwards_type_and_values(self, qt_app, stub_dialog):
        editor = _RecordingEditor()
        stub_dialog.result = _result(CseqEventType.REVERB, 64, 0, 12)

        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=editor,
        )
        dialog._event_table.selectRow(0)
        dialog._do_insert_event()

        assert editor.calls == [
            ("insert_event", (0, 0, CseqEventType.REVERB, 64, 0, 12)),
        ]

    def test_cancelled_dialog_does_not_call_back(self, qt_app, stub_dialog):
        editor = _RecordingEditor()
        stub_dialog.accepted = False
        stub_dialog.result = _result(CseqEventType.PAN, 1)

        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=editor,
        )
        dialog._event_table.selectRow(0)
        dialog._do_edit_event()

        assert editor.calls == []

    def test_delete_forwards_indices(self, qt_app):
        editor = _RecordingEditor()
        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=editor,
        )
        dialog._event_table.selectRow(0)
        dialog._do_delete_event()

        assert editor.calls == [("delete_event", (0, 0))]

    def test_replace_track_forwards_the_track_row(self, qt_app):
        editor = _RecordingEditor()
        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=editor,
        )
        dialog._track_list.setCurrentRow(0)
        dialog._fire_replace()

        assert editor.calls == [("replace_track_from_midi", (0,))]

    def test_drum_context_is_passed_to_the_edit_dialog(self, qt_app, stub_dialog):
        stub_dialog.result = _result(CseqEventType.NOTE_ON, 13)

        dialog = TrackEventsDialog(
            None, "t",
            _song(
                CseqEvent(delta=0, event_type=CseqEventType.NOTE_ON, pitch=13, velocity=99),
                is_drum=True,
            ),
            editor=_RecordingEditor(),
            percussion_count=16,
        )
        dialog._event_table.selectRow(0)
        dialog._do_edit_event()

        assert stub_dialog.last_kwargs["is_drum"] is True
        assert stub_dialog.last_kwargs["descriptor_count"] == 16


class TestApplyRefresh:

    def test_none_result_leaves_the_table_alone(self, qt_app):
        song = _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128))
        dialog = TrackEventsDialog(None, "t", song, editor=_RecordingEditor())
        before = dialog._event_table.rowCount()

        dialog._apply(None)

        assert dialog._event_table.rowCount() == before
        assert dialog._song is song

    def test_adopts_the_returned_song(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=_RecordingEditor(),
        )
        dialog._event_table.selectRow(0)

        replacement = _song(
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64),
            CseqEvent(delta=0, event_type=CseqEventType.REVERB, pitch=32),
        )
        dialog._apply(replacement)

        assert dialog._song is replacement
        assert dialog._event_table.rowCount() == 3
        assert dialog._event_table.item(0, 2).text() == "pan=64"

    def test_track_label_follows_the_new_event_count(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t",
            _song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=128)),
            editor=_RecordingEditor(),
        )
        dialog._event_table.selectRow(0)

        dialog._apply(_song(
            CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=64),
            CseqEvent(delta=0, event_type=CseqEventType.REVERB, pitch=32),
        ))

        assert "3 events" in dialog._track_list.item(0).text()

    def test_selection_clamps_when_the_track_shrinks(self, qt_app):
        dialog = TrackEventsDialog(
            None, "t",
            _song(
                CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=1),
                CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=2),
                CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=3),
            ),
            editor=_RecordingEditor(),
        )
        dialog._event_table.selectRow(3)

        dialog._apply(_song(CseqEvent(delta=0, event_type=CseqEventType.PAN, pitch=1)))

        assert dialog._selected_event_index() == 1
