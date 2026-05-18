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

        for widget in self._collect("player_widgets"):
            widget.clear()

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
            song_blob = self._window.hwl.songs[song_index]
            label = f"Song {song_index} Seq {seq_index}"

            def render() -> bytes | None:
                lookup = self._window._sample_lookup
                cseq = self._window._cseq_reader.read(song_blob)
                if seq_index >= len(cseq.songs):
                    return None

                sample_data = lookup.collect_song_samples(self._window.hwl, cseq)

                self._window.status.showMessage(
                    f"Rendering song {song_index} sequence {seq_index}...",
                )
                QApplication.processEvents()

                return self._window._cseq_renderer.render_song_to_wav(
                    cseq, seq_index, sample_data,
                )

            wav = self._get_or_render_wav(song_blob, seq_index, None, render)
            if wav is None:
                return

            self._play_wav(wav, label, lambda: self.play_sequence(song_index, seq_index))
        except Exception as e:
            self._window.status.showMessage(f"Playback failed: {e}")

    def play_hub(
        self, song_index: int, sub_song_index: int,
        active_tracks: list[int], label: str,
    ) -> None:
        """Render and play the Adventure Hub main-music sub-song with only
        the tracks audible in the selected hub world.

        Mirrors CTR's runtime behaviour: every track stays armed, the per-hub
        bitmask (Cseq.hubTracksMask) mutes those whose bit isn't set for the
        current hub. See CTR-tools CseqSong.cs:148-151.
        """
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        if not active_tracks:
            self._window.status.showMessage("No tracks audible in this hub")
            return

        try:
            song_blob = self._window.hwl.songs[song_index]
            track_key = tuple(active_tracks)

            def render() -> bytes | None:
                lookup = self._window._sample_lookup
                cseq = self._window._cseq_reader.read(song_blob)
                sample_data = lookup.collect_song_samples(self._window.hwl, cseq)

                self._window.status.showMessage(
                    f"Rendering {label} ({len(active_tracks)} tracks)...",
                )
                QApplication.processEvents()

                return self._window._cseq_renderer.render_song_to_wav(
                    cseq, sub_song_index, sample_data, active_tracks=active_tracks,
                )

            wav = self._get_or_render_wav(song_blob, sub_song_index, track_key, render)
            if wav is None:
                return

            self._play_wav(
                wav, label,
                lambda: self.play_hub(song_index, sub_song_index, active_tracks, label),
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
        """Common path: play WAV, update all player bars, optionally update
        all waveforms. Each tab owns its own widgets but they all observe the
        same QMediaPlayer, so transport state stays consistent."""
        self._window._audio_player.play_wav(wav)
        self._window.status.showMessage(f"Playing {label}")

        for widget in self._collect("player_widgets"):
            widget.set_now_playing(label, replay_callback)

        if update_waveform:
            for waveform in self._collect("waveforms"):
                waveform.set_wav(wav)
                waveform.setVisible(True)

    def _get_or_render_wav(
        self, song_blob: bytes, sub_song_index: int,
        active_tracks: tuple[int, ...] | None, render_fn,
    ) -> bytes | None:
        """Resolve a song render through the two-tier AudioCache. Memory hits
        return instantly; disk hits avoid the (slow) Python mix loop entirely
        across app restarts."""
        cache = self._window._audio_cache
        banks = tuple(self._window.hwl.banks) if self._window.hwl else ()

        if cache is not None:
            key = cache.make_key(song_blob, sub_song_index, banks, active_tracks)
            wav = cache.get(key)
            if wav is not None:
                return wav

            wav = render_fn()
            if wav:
                cache.put(key, wav)

            return wav

        return render_fn()

    def clear_render_cache(self) -> None:
        if self._window._audio_cache is not None:
            self._window._audio_cache.clear_memory()

    def _collect(self, attr: str) -> list:
        """Pull a list-of-widgets attribute off the main window, defaulting to
        the legacy single-attribute name when the list isn't there yet."""
        widgets = getattr(self._window, attr, None)
        if widgets is not None:
            return list(widgets)

        single = getattr(self._window, attr.rstrip("s"), None)
        return [single] if single is not None else []

    def _show_no_audio(self) -> None:
        if not self.can_play():
            self._window.status.showMessage("Audio playback not available (QtMultimedia not found)")
