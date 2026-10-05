# coding: utf-8

import pytest

from howl_editor.ctr.voice.pitch_stepper import PitchStepper
from howl_editor.ps1 import spu

UNITY = 4096


@pytest.fixture
def stepper():
    return PitchStepper()


class TestOctaves:

    def test_up_doubles(self, stepper):
        assert stepper.octaves(UNITY, 1) == 2 * UNITY

    def test_down_halves(self, stepper):
        assert stepper.octaves(UNITY, -1) == UNITY // 2

    def test_round_trips_exactly(self, stepper):
        assert stepper.octaves(stepper.octaves(1234, 1), -1) == 1234

    def test_stops_at_the_highest_pitch_the_spu_plays(self, stepper):
        # 2x doubles to 0x4000, one register above what the SPU plays.
        assert stepper.octaves(2 * UNITY, 1) == spu.MAX_PITCH

    def test_repeated_steps_never_pass_the_ceiling(self, stepper):
        register = UNITY

        for _ in range(8):
            register = stepper.octaves(register, 1)

        assert register == spu.MAX_PITCH
        assert not stepper.exceeds_playable_ceiling(register)

    def test_a_register_above_the_ceiling_is_not_dragged_down(self, stepper):
        """A modded file can hold one; stepping up must not quietly retune it."""
        above = spu.MAX_PITCH * 2

        assert stepper.octaves(above, 1) == above

    def test_a_register_above_the_ceiling_can_come_back_down(self, stepper):
        assert stepper.octaves(spu.MAX_PITCH * 2, -1) == spu.MAX_PITCH

    def test_a_step_of_no_octaves_changes_nothing(self, stepper):
        assert stepper.octaves(spu.MAX_PITCH * 2, 0) == spu.MAX_PITCH * 2

    def test_never_falls_to_silence(self, stepper):
        # 0 would stop the sample advancing at all.
        assert stepper.octaves(1, -1) == 1

    def test_zero_stays_zero(self, stepper):
        assert stepper.octaves(0, 1) == 0


class TestSemitones:

    def test_twelve_semitones_match_an_octave(self, stepper):
        assert stepper.semitones(UNITY, 12) == stepper.octaves(UNITY, 1)

    def test_one_semitone_up_is_the_tempered_ratio(self, stepper):
        assert stepper.semitones(UNITY, 1) == round(UNITY * 2 ** (1 / 12))

    def test_down_is_the_inverse_direction(self, stepper):
        assert stepper.semitones(UNITY, -1) < UNITY

    def test_thirteen_semitones_is_an_octave_plus_one(self, stepper):
        assert stepper.semitones(UNITY, 13) == round(2 * UNITY * 2 ** (1 / 12))

    def test_stops_at_the_highest_pitch_the_spu_plays(self, stepper):
        assert stepper.semitones(spu.MAX_PITCH, 1) == spu.MAX_PITCH


class TestCeiling:

    def test_at_the_ceiling_is_playable(self, stepper):
        assert stepper.exceeds_playable_ceiling(spu.MAX_PITCH) is False

    def test_above_the_ceiling_plays_flat(self, stepper):
        assert stepper.exceeds_playable_ceiling(spu.MAX_PITCH + 1) is True
