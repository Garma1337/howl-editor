# coding: utf-8

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from howl_editor.ctr.formats.cseq.models import CseqEventType
from howl_editor.gui.dialog.edit_event_dialog import EditEventDialog


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


class TestChosen:

    def test_returns_edited_values(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=13, velocity=99, delta=5,
        )
        dialog._pitch.setValue(14)
        dialog._velocity.setValue(80)
        dialog._delta.setValue(7)

        result = dialog.chosen()

        assert result.event_type == CseqEventType.NOTE_ON
        assert result.pitch == 14
        assert result.velocity == 80
        assert result.delta == 7

    def test_insert_mode_reports_selected_type(self, qt_app):
        dialog = EditEventDialog(None, None, pitch=0)
        index = dialog._type_combo.findData(CseqEventType.REVERB)
        dialog._type_combo.setCurrentIndex(index)

        assert dialog.chosen().event_type == CseqEventType.REVERB

    def test_clamps_initial_values_into_byte_range(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=9999, velocity=-5,
        )

        assert dialog.chosen().pitch == 255
        assert dialog.chosen().velocity == 0


class TestVelocityVisibility:
    """NOTE_ON is the only two-parameter opcode, so the velocity field must
    appear for it and stay hidden everywhere else."""

    def test_velocity_shown_for_note_on(self, qt_app):
        dialog = EditEventDialog(None, CseqEventType.NOTE_ON, pitch=1)

        assert not dialog._velocity.isHidden()

    @pytest.mark.parametrize("event_type", [
        CseqEventType.NOTE_OFF,
        CseqEventType.PAN,
        CseqEventType.PITCH_BEND,
        CseqEventType.REVERB,
        CseqEventType.CHANGE_PATCH,
    ])
    def test_velocity_hidden_for_single_param_events(self, qt_app, event_type):
        dialog = EditEventDialog(None, event_type, pitch=1)

        assert dialog._velocity.isHidden()

    def test_velocity_follows_type_change_in_insert_mode(self, qt_app):
        dialog = EditEventDialog(None, None, pitch=0)

        dialog._type_combo.setCurrentIndex(dialog._type_combo.findData(CseqEventType.NOTE_ON))
        assert not dialog._velocity.isHidden()

        dialog._type_combo.setCurrentIndex(dialog._type_combo.findData(CseqEventType.PAN))
        assert dialog._velocity.isHidden()


class TestParameterLabelling:
    """A drum track's note byte is a percussion-table index, not a pitch. The
    label is the only thing telling the user which one they're editing."""

    def test_drum_note_labelled_as_percussion_index(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=13, is_drum=True,
        )

        assert dialog._pitch_row_label.text() == "Percussion index:"

    def test_melodic_note_labelled_as_note(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=60, is_drum=False,
        )

        assert dialog._pitch_row_label.text() == "Note:"

    def test_change_patch_labelled_as_instrument_index(self, qt_app):
        dialog = EditEventDialog(None, CseqEventType.CHANGE_PATCH, pitch=2)

        assert dialog._pitch_row_label.text() == "Instrument index:"

    def test_modulation_keeps_generic_value_label(self, qt_app):
        dialog = EditEventDialog(None, CseqEventType.PITCH_BEND, pitch=128)

        assert dialog._pitch_row_label.text() == "Value:"

    def test_drum_blurb_states_the_legal_index_range(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=13,
            is_drum=True, descriptor_count=16,
        )

        assert "0–15" in dialog._blurb.text()

    def test_blurb_omits_range_when_count_unknown(self, qt_app):
        dialog = EditEventDialog(
            None, CseqEventType.NOTE_ON, pitch=13, is_drum=True,
        )

        assert "descriptors" not in dialog._blurb.text()


class TestDescribe:

    @pytest.mark.parametrize(("value", "expected"), [
        (0x80, "no bend (neutral)"),
        (0xC0, "+1.00 semitones"),
        (0x40, "-1.00 semitones"),
        (0x00, "-2.00 semitones"),
    ])
    def test_pitch_bend_reads_as_semitones(self, value, expected):
        assert EditEventDialog.describe(CseqEventType.PITCH_BEND, value) == expected

    def test_pan_centre(self):
        assert EditEventDialog.describe(CseqEventType.PAN, 0x80) == "centre"

    def test_pan_sides(self):
        assert "left" in EditEventDialog.describe(CseqEventType.PAN, 0x10)
        assert "right" in EditEventDialog.describe(CseqEventType.PAN, 0xF0)

    def test_reverb_zero_is_off(self):
        assert EditEventDialog.describe(CseqEventType.REVERB, 0) == "off"

    def test_note_describes_by_track_flavour(self):
        assert EditEventDialog.describe(CseqEventType.NOTE_ON, 13, is_drum=True) == "percussion #13"
        assert EditEventDialog.describe(CseqEventType.NOTE_ON, 60, is_drum=False) == "note 60"
