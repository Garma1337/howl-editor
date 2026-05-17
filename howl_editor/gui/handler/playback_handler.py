# coding: utf-8

from PySide6.QtWidgets import QApplication


class PlaybackHandler:

    def __init__(self, window):
        self._window = window

    def can_play(self) -> bool:
        return self._window._audio_player is not None and self._window._audio_player.available

    def stop(self) -> None:
        if self._window._audio_player:
            self._window._audio_player.stop()
            self._window.status.showMessage("Playback stopped")

        if hasattr(self._window, "player_widget"):
            self._window.player_widget.clear()

    def play_sample(self, bank_index: int, sample_index: int) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            lookup = self._window._sample_lookup
            samples = self._window._bank_reader.parse(
                self._window.hwl.banks[bank_index], self._window.hwl.spu_addrs,
            )
            if sample_index >= len(samples):
                return

            sample = samples[sample_index]
            sample_rate = lookup.lookup_sample_rate(self._window.hwl, sample.spu_index)
            wav = self._window._vag_decoder.decode_to_wav(sample.data, sample_rate)
            label = f"SPU {sample.spu_index}"

            self._play_wav(
                wav, label, lambda: self.play_sample(bank_index, sample_index),
                update_waveform=False,
            )
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_sequence(self, song_index: int, seq_index: int) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            lookup = self._window._sample_lookup
            cseq = self._window._cseq_reader.read(self._window.hwl.songs[song_index])
            if seq_index >= len(cseq.songs):
                return

            sample_data = lookup.collect_song_samples(self._window.hwl, cseq)

            self._window.status.showMessage(f"Rendering song {song_index} sequence {seq_index}...")
            QApplication.processEvents()

            wav = self._window._cseq_renderer.render_song_to_wav(cseq, seq_index, sample_data)
            label = f"Song {song_index} Seq {seq_index}"

            self._play_wav(wav, label, lambda: self.play_sequence(song_index, seq_index))
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_layered(self, song_index: int, seq_indices: list[int], label: str) -> None:
        """Render and play several sequences mixed together (Adventure Hub preview).

        The mix mirrors what CTR's runtime does when multiple sequences in the
        hub song are unmuted simultaneously by `advHubSongSetBytes`.
        """
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        if not seq_indices:
            self._window.status.showMessage("No sequences to preview for this hub")
            return

        try:
            lookup = self._window._sample_lookup
            cseq = self._window._cseq_reader.read(self._window.hwl.songs[song_index])
            sample_data = lookup.collect_song_samples(self._window.hwl, cseq)

            self._window.status.showMessage(
                f"Rendering {label} ({len(seq_indices)} layered sequences)...",
            )
            QApplication.processEvents()

            wav = self._window._cseq_renderer.render_layered_to_wav(
                cseq, seq_indices, sample_data,
            )

            self._play_wav(
                wav, label,
                lambda: self.play_layered(song_index, seq_indices, label),
            )
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_other_fx(self, index: int) -> None:
        if not self._window.hwl or index >= len(self._window.hwl.other_fx):
            return

        fx = self._window.hwl.other_fx[index]
        self._play_fx_sample(fx.spu_index, fx.pitch, f"FX {index}")

    def play_engine_fx(self, index: int) -> None:
        if not self._window.hwl or index >= len(self._window.hwl.engine_fx):
            return

        fx = self._window.hwl.engine_fx[index]
        self._play_fx_sample(fx.spu_index, fx.pitch, f"Engine {index}")

    def _play_fx_sample(self, spu_index: int, pitch: int, label: str) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            lookup = self._window._sample_lookup
            data = lookup.find_sample_data(self._window.hwl, spu_index)
            if data is None:
                self._window.status.showMessage(f"SPU {spu_index} not found in any bank")
                return

            sample_rate = int(pitch / 4096 * 44100) if pitch > 0 else 11025
            wav = self._window._vag_decoder.decode_to_wav(data, sample_rate)

            self._play_wav(
                wav, f"{label} (SPU {spu_index}, {sample_rate} Hz)",
                update_waveform=False,
            )
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def _play_wav(
        self, wav: bytes, label: str, replay_callback=None, update_waveform: bool = True,
    ) -> None:
        """Common path: play WAV, update player bar, optionally show waveform."""
        self._window._audio_player.play_wav(wav)
        self._window.status.showMessage(f"Playing {label}")

        if hasattr(self._window, "player_widget"):
            self._window.player_widget.set_now_playing(label, replay_callback)

        if update_waveform and hasattr(self._window, "waveform"):
            self._window.waveform.set_wav(wav)
            self._window.waveform.setVisible(True)

    def _show_no_audio(self) -> None:
        if not self.can_play():
            self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")
