# coding: utf-8

from howl_editor.ctr.audio_settings import NOTE_FREQUENCY
from howl_editor.ctr.voice.pitch_calculator import PitchCalculator
from howl_editor.ctr.voice.pitch_headroom import PitchHeadroomInspector


class TestInspect:

    def setup_method(self):
        self.inspector = PitchHeadroomInspector(PitchCalculator())

    def test_a_gentle_base_pitch_is_clean_across_the_keyboard(self):
        top = len(NOTE_FREQUENCY) - 1
        headroom = self.inspector.inspect(0x400, list(range(0, top + 1)))

        assert headroom.is_clean
        assert headroom.garbage is False
        assert headroom.highest_note == top

    def test_no_notes_is_clean(self):
        headroom = self.inspector.inspect(0x2000, [])

        assert headroom.is_clean
        assert headroom.highest_note is None

    def test_a_capped_note_is_flagged_without_garbage(self):
        # base 4096, note 84 -> register 0x4000: over the 4.0x ceiling but not
        # wrapped, so the cap catches it and it plays flat rather than garbage.
        headroom = self.inspector.inspect(4096, [60, 84])

        assert headroom.affected_notes == 1
        assert headroom.garbage is False

    def test_a_note_wrapping_below_the_cap_is_garbage(self):
        # base 0x2000, note 96 -> true 0x10000 wraps to 0x0000, below the cap.
        headroom = self.inspector.inspect(0x2000, [96])

        assert headroom.affected_notes == 1
        assert headroom.garbage is True

    def test_a_wrap_that_lands_above_the_cap_is_flat_not_garbage(self):
        # base 0x2000, note 100 -> wraps to 0x428A, still above the 4.0x cap.
        headroom = self.inspector.inspect(0x2000, [100])

        assert headroom.affected_notes == 1
        assert headroom.garbage is False

    def test_counts_every_offending_note_and_reports_the_top(self):
        headroom = self.inspector.inspect(0x2000, [60, 84, 96])

        assert headroom.affected_notes == 2  # 84 caps flat, 96 wraps to garbage
        assert headroom.garbage is True
        assert headroom.highest_note == 96


class TestHighestSafeBasePitch:

    def setup_method(self):
        self.inspector = PitchHeadroomInspector(PitchCalculator())

    def test_none_without_notes(self):
        assert self.inspector.highest_safe_base_pitch([]) is None

    def test_lands_exactly_on_the_boundary(self):
        # For note 84 the register is 4x the base, so the ceiling (0x3FFF) is
        # reached at base 4095; 4096 tips it over.
        safe = self.inspector.highest_safe_base_pitch([84])

        assert safe == 4095
        assert self.inspector.inspect(safe, [84]).is_clean
        assert not self.inspector.inspect(safe + 1, [84]).is_clean

    def test_constrained_by_the_highest_note(self):
        # The top note binds the limit; adding lower notes doesn't change it.
        assert (
            self.inspector.highest_safe_base_pitch([60, 72, 84])
            == self.inspector.highest_safe_base_pitch([84])
        )
