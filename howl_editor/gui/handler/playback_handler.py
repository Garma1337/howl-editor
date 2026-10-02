# coding: utf-8

from howl_editor.ctr import render_job
from howl_editor.ps1 import spu

_MIN_PLAYBACK_RATE = 8000
_MAX_PLAYBACK_RATE = 48000
_DEFAULT_SAMPLE_RATE = 11025
_OUTPUT_RATE = 22050


class PlaybackHandler:

    def __init__(self, window):
        self._window = window
        self._render = None

    def can_play(self) -> bool:
        return self._window._audio_player is not None and self._window._audio_player.available

    def stop(self) -> None:
        self._abandon_render()

        if self._window._audio_player:
            self._window._audio_player.stop()

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
            raw_rate = lookup.lookup_sample_rate(self._window.hwl, sample.spu_index)
            wav, resample_note = self._render_wav(sample.data, raw_rate)
            label = f"SPU {sample.spu_index}{resample_note}"

            self._play_wav(
                wav, label, lambda: self.play_sample(bank_index, sample_index),
                update_waveform=False,
            )
        except Exception as e:
            self._window._notify_danger(f"Playback failed: {e}")

    def play_sequence(self, song_index: int, seq_index: int) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            song_blob = self._window.hwl.songs[song_index]
            label = f"Song {song_index} Seq {seq_index}"

            def render_args():
                cseq = self._window._cseq_parses.read(song_blob)
                if seq_index >= len(cseq.songs):
                    return None

                return (cseq, seq_index, self._collect_samples(cseq))

            self._render_then_play(
                song_blob, seq_index, None, label, render_args,
                lambda: self.play_sequence(song_index, seq_index),
            )
        except Exception as e:
            self._window._notify_danger(f"Playback failed: {e}")

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
            self._window._notify_warning("No tracks audible in this hub")
            return

        try:
            song_blob = self._window.hwl.songs[song_index]
            track_key = tuple(active_tracks)

            def render_args():
                cseq = self._window._cseq_parses.read(song_blob)

                return (
                    cseq, sub_song_index, self._collect_samples(cseq),
                    _OUTPUT_RATE, list(active_tracks),
                )

            self._render_then_play(
                song_blob, sub_song_index, track_key, label, render_args,
                lambda: self.play_hub(song_index, sub_song_index, active_tracks, label),
            )
        except Exception as e:
            self._window._notify_danger(f"Playback failed: {e}")

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

    def play_spu_sample(self, spu_index: int, pitch: int, label: str) -> None:
        self._play_fx_sample(spu_index, pitch, label)

    def _play_fx_sample(self, spu_index: int, pitch: int, label: str) -> None:
        if not self._window.hwl or not self.can_play():
            self._show_no_audio()
            return

        try:
            lookup = self._window._sample_lookup
            data = lookup.find_sample_data(self._window.hwl, spu_index)
            if data is None:
                self._window._notify_warning(f"SPU {spu_index} not found in any bank")
                return

            raw_rate = (
                int(pitch / spu.FREQUENCY_UNIT * spu.SAMPLE_RATE)
                if pitch > 0 else _DEFAULT_SAMPLE_RATE
            )
            wav, resample_note = self._render_wav(data, raw_rate)

            self._play_wav(
                wav, f"{label} (SPU {spu_index}, {raw_rate} Hz{resample_note})",
                update_waveform=False,
            )
        except Exception as e:
            self._window._notify_danger(f"Playback failed: {e}")

    def _render_wav(self, vag_data: bytes, raw_rate: int) -> tuple[bytes, str]:
        """Decode VAG → PCM at its intended rate, then resample into a
        backend-playable rate when the original falls outside the window
        QMediaPlayer accepts. Audible pitch is preserved across the bump."""
        if _MIN_PLAYBACK_RATE <= raw_rate <= _MAX_PLAYBACK_RATE:
            return self._window._vag_decoder.decode_to_wav(vag_data, raw_rate), ""

        target_rate = _DEFAULT_SAMPLE_RATE
        pcm = self._window._vag_decoder.decode(vag_data)
        resampled = self._window._resampler.resample(pcm, raw_rate, target_rate)
        wav = self._window._wav_writer.write(resampled, target_rate, channels=1)

        return wav, f" — resampled {raw_rate}→{target_rate} Hz"

    def _play_wav(
        self, wav: bytes, label: str, replay_callback=None, update_waveform: bool = True,
    ) -> None:
        """Common path: play WAV, update all player bars, optionally update
        all waveforms. Each tab owns its own widgets but they all observe the
        same QMediaPlayer, so transport state stays consistent."""
        self._window._audio_player.play_wav(wav)

        for widget in self._collect("player_widgets"):
            widget.set_now_playing(label, replay_callback)

        if update_waveform:
            for waveform in self._collect("waveforms"):
                waveform.set_wav(wav)
                waveform.setVisible(True)

    def _render_then_play(
        self, song_blob: bytes, sub_song_index: int,
        active_tracks: tuple[int, ...] | None, label: str, build_args,
        replay_callback,
    ) -> None:
        """Play a song render, mixing it in a separate process (see
        ProcessTaskRunner) when it is not already cached.

        `build_args` is only called on a cache miss: gathering a song's samples
        means parsing every bank, and doing that for a replay would put the
        very stall this path exists to avoid back on the GUI thread."""
        cached = self._cached_wav(song_blob, sub_song_index, active_tracks)

        if cached is not None:
            self._play_wav(cached, label, replay_callback)
            return

        render_args = build_args()
        if render_args is None:
            return

        self._abandon_render()
        busy = self._window.notifications.push_busy(f"Rendering {label}…")
        handle = None

        def done(wav: bytes | None) -> None:
            if self._render is not handle:
                return

            self._render = None

            if not wav:
                busy.failed(f"{label} produced no audio")
                return

            self._store_wav(song_blob, sub_song_index, active_tracks, wav)
            busy.dismiss()
            self._play_wav(wav, label, replay_callback)

        handle = self._window._process_tasks.run(
            render_job.render_song_wav, render_args,
            on_success=done,
            on_error=lambda message: busy.failed(f"Rendering {label} failed: {message}"),
            on_cancelled=busy.dismiss,
            on_progress=busy.set_progress,
        )
        self._render = handle
        busy.set_cancel(handle.cancel)

    def _abandon_render(self) -> None:
        """Asking for a second render supersedes the first. Without this the
        older mix finishes later and starts playing over whatever the user
        asked for in the meantime."""
        if self._render is not None:
            self._render.cancel()
            self._render = None

    def _collect_samples(self, cseq) -> dict[int, bytes]:
        return self._window._sample_lookup.collect_song_samples(self._window.hwl, cseq)

    def _cached_wav(
        self, song_blob: bytes, sub_song_index: int, active_tracks: tuple[int, ...] | None,
    ) -> bytes | None:
        cache = self._window._audio_cache

        if cache is None:
            return None

        return cache.get(self._cache_key(cache, song_blob, sub_song_index, active_tracks))

    def _store_wav(
        self, song_blob: bytes, sub_song_index: int,
        active_tracks: tuple[int, ...] | None, wav: bytes,
    ) -> None:
        cache = self._window._audio_cache

        if cache is not None:
            cache.put(self._cache_key(cache, song_blob, sub_song_index, active_tracks), wav)

    def _cache_key(
        self, cache, song_blob: bytes, sub_song_index: int,
        active_tracks: tuple[int, ...] | None,
    ):
        banks = tuple(self._window.hwl.banks) if self._window.hwl else ()
        return cache.make_key(song_blob, sub_song_index, banks, active_tracks)

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
            self._window._notify_warning("Audio playback not available (QtMultimedia not found)")
