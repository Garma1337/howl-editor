# coding: utf-8

from howl_editor.audio.settings.ctr import MASTER_MUSIC_VOL, DEFAULT_SONG_VOL, VOLUME_LR


class GainCalculator:
    """Computes somewhat CTR-accurate stereo gain values from the volume chain.

    Tries to match h41_howl_InitChannelAttr_Music and h72_Channel_SetVolume.
    """

    _SPU_MAX_VOL = 0x3FFF
    _GAIN_DIVISOR = float(_SPU_MAX_VOL * 0xFF)

    def compute(
        self, inst_vol: int, note_vel: int, seq_vol: int, pan: int,
    ) -> tuple[float, float]:
        """Return (gain_l, gain_r) in [0, 1] range."""
        base = (MASTER_MUSIC_VOL * DEFAULT_SONG_VOL * seq_vol) >> 10
        sample_vol = base * inst_vol
        final_vol = min((sample_vol * note_vel) >> 15, self._SPU_MAX_VOL)

        lr = max(0, min(255, pan))
        gain_l = (final_vol * VOLUME_LR[0xFF - lr]) / self._GAIN_DIVISOR
        gain_r = (final_vol * VOLUME_LR[lr]) / self._GAIN_DIVISOR

        return gain_l, gain_r
