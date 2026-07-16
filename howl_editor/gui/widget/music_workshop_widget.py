# coding: utf-8

from dataclasses import dataclass
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QScrollArea, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from howl_editor.ctr.diagnostics.howl_diagnostics import Target, TargetKind
from howl_editor.ctr.formats.cseq.models import CseqFile, CseqInstrument, CseqPercussion
from howl_editor.ctr.formats.cseq.reader import CseqReader
from howl_editor.ctr.formats.howl.models import HowlFile
from howl_editor.ctr.sample_lookup import SampleLookup
from howl_editor.gui.layout import ButtonWidth
from howl_editor.gui.size_formatter import SizeFormatter
from howl_editor.gui.stylesheet_loader import StylesheetLoader
from howl_editor.gui.widget.player_widget import PlayerWidget
from howl_editor.gui.widget.waveform_widget import WaveformWidget
from howl_editor.midi.drum_name_resolver import DrumNameResolver

_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


@dataclass(frozen=True)
class SampleActionTarget:
    """Coordinates for replace / copy / export on an instrument's sample.

    Workshop rows display SPU indices, but the existing SampleHandler
    expects (bank, slot) — we resolve once on row construction so the
    button callbacks have everything they need."""
    spu_index: int
    bank_index: int | None
    sample_index: int | None
    label: str


class MusicWorkshopWidget(QWidget):

    sig_play_instrument = Signal(int, int, str)  # spu_index, pitch, label
    sig_play_sequence = Signal(int, int)         # song_index, seq_index
    sig_replace_sequence = Signal(int, int)
    sig_copy_sequence = Signal(int, int)
    sig_export_sequence = Signal(int, int, str)  # song_index, seq_index, label
    sig_remove_sequence = Signal(int, int)
    sig_view_sequence_events = Signal(int, int)  # song_index, seq_index
    sig_replace_sample = Signal(int, int)        # bank_index, sample_index
    sig_copy_sample = Signal(int, int)
    sig_export_sample = Signal(int, int)
    sig_edit_instrument = Signal(int, int)       # song_index, inst_index
    sig_edit_percussion = Signal(int, int)       # song_index, perc_index
    sig_retarget_instrument = Signal(int, int)   # song_index, inst_index
    sig_retarget_percussion = Signal(int, int)   # song_index, perc_index

    def __init__(
        self,
        cseq_reader: CseqReader,
        sample_lookup: SampleLookup,
        drum_names: DrumNameResolver,
        size_formatter: SizeFormatter,
        stylesheet_loader: StylesheetLoader,
        severity_presenter=None,
    ):
        super().__init__()
        self._cseq_reader = cseq_reader
        self._sample_lookup = sample_lookup
        self._drum_names = drum_names
        self._sizes = size_formatter
        self._stylesheets = stylesheet_loader
        self._severity_presenter = severity_presenter
        self._hwl: HowlFile | None = None
        self._song_count = 0
        self._diag_index = None
        self._build_ui()

    def refresh(self, hwl: HowlFile | None, diag_index=None) -> None:
        self._diag_index = diag_index
        # Hold onto the previous selection so an edit-triggered rebuild
        # doesn't drag the user back to song 0 mid-task. -1 sentinel covers
        # both "no prior selection" and "song list was empty."
        previous_row = self._song_list.currentRow()

        self._hwl = hwl
        self._song_count = len(hwl.songs) if hwl else 0
        self._populate_song_list()

        if self._song_count == 0:
            self._show_empty_detail()
            return

        target_row = previous_row if 0 <= previous_row < self._song_count else 0
        self._song_list.setCurrentRow(target_row)

    def _build_ui(self) -> None:
        self.setObjectName("musicWorkshopRoot")
        self.setStyleSheet(self._stylesheets.load("music_workshop.qss"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_song_list())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([260, 840])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, stretch=1)

        outer.addWidget(self._build_player_dock())

    def _build_player_dock(self) -> QWidget:
        """Persistent waveform + transport at the bottom of the Workshop tab.
        Mirrors the Category Browser's docked player — music makers usually
        audition many things in sequence, so the controls stay put rather
        than appearing per-row."""
        dock = QFrame()
        dock.setObjectName("workshopPlayerDock")

        layout = QVBoxLayout(dock)
        layout.setContentsMargins(12, 6, 12, 8)
        layout.setSpacing(4)

        self.waveform = WaveformWidget()
        self.waveform.setVisible(False)
        layout.addWidget(self.waveform)

        self.player_widget = PlayerWidget()
        layout.addWidget(self.player_widget)

        return dock

    def _build_song_list(self) -> QWidget:
        container = QWidget()
        container.setObjectName("workshopSongPanel")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 6, 12)
        layout.setSpacing(6)

        heading = QLabel("Songs")
        heading.setObjectName("workshopSectionLabel")
        layout.addWidget(heading)

        self._song_list = QListWidget()
        self._song_list.setObjectName("workshopSongList")
        self._song_list.currentRowChanged.connect(self._on_song_selected)
        layout.addWidget(self._song_list, stretch=1)

        return container

    def _build_detail_panel(self) -> QWidget:
        self._detail_scroll = QScrollArea()
        self._detail_scroll.setObjectName("workshopDetailScroll")
        self._detail_scroll.setWidgetResizable(True)
        self._detail_scroll.setFrameShape(QScrollArea.NoFrame)

        self._detail_inner = QWidget()
        self._detail_inner.setObjectName("workshopDetailInner")
        self._detail_layout = QVBoxLayout(self._detail_inner)
        self._detail_layout.setContentsMargins(20, 16, 20, 20)
        self._detail_layout.setSpacing(14)

        self._show_empty_detail()
        self._detail_scroll.setWidget(self._detail_inner)
        return self._detail_scroll

    def _populate_song_list(self) -> None:
        self._song_list.blockSignals(True)
        self._song_list.clear()

        if self._hwl is None:
            self._song_list.blockSignals(False)
            return

        for i, blob in enumerate(self._hwl.songs):
            name = self._cseq_reader.get_name(i)
            label = f"Song {i} — {name}" if name else f"Song {i}"

            try:
                cseq = self._cseq_reader.read(blob)
                summary = (
                    f"{cseq.songs[0].bpm} BPM · "
                    f"{len(cseq.songs[0].tracks)} tracks"
                    if cseq.songs else "empty"
                )
            except Exception:
                summary = "unreadable"

            emoji, tooltip = self._song_badge(i)
            prefix = f"{emoji} " if emoji else ""
            item = QListWidgetItem(f"{prefix}{label}\n{summary}")
            item.setData(Qt.UserRole, i)
            if tooltip:
                item.setToolTip(tooltip)

            self._song_list.addItem(item)

        self._song_list.blockSignals(False)

    def _on_song_selected(self, row: int) -> None:
        if row < 0 or self._hwl is None or row >= len(self._hwl.songs):
            self._show_empty_detail()
            return

        try:
            cseq = self._cseq_reader.read(self._hwl.songs[row])
        except Exception as e:
            self._render_error(f"Cannot read song {row}: {e}")
            return

        self._render_song(row, cseq)

    def _render_song(self, song_index: int, cseq: CseqFile) -> None:
        self._clear_detail()

        name = self._cseq_reader.get_name(song_index)
        title_text = f"Song {song_index} — {name}" if name else f"Song {song_index}"
        title = QLabel(title_text)
        title.setObjectName("workshopTitle")
        self._detail_layout.addWidget(title)

        banner = self._build_diagnosis_banner(song_index)
        if banner is not None:
            self._detail_layout.addWidget(banner)

        self._detail_layout.addWidget(self._build_song_header(cseq))
        self._detail_layout.addWidget(self._build_sequences_section(song_index, cseq))
        self._detail_layout.addWidget(self._build_instruments_section(song_index, cseq.instruments))
        self._detail_layout.addWidget(self._build_percussion_section(song_index, cseq.percussions))
        self._detail_layout.addStretch(1)

    def _song_findings(self, song_index: int) -> list:
        """Song-level diagnosis findings (too big for the buffer, broken sample
        references) — the problems a music editor can act on."""
        if self._diag_index is None:
            return []

        return self._diag_index.findings_for(Target(TargetKind.SONG, song_index))

    def _worst_severity(self, findings):
        if not findings:
            return None

        return max((f.severity for f in findings), key=lambda s: s.value)

    def _song_badge(self, song_index: int) -> tuple[str, str]:
        """(emoji, tooltip) for a song-list row, '' when clean."""
        findings = self._song_findings(song_index)
        worst = self._worst_severity(findings)
        if worst is None or self._severity_presenter is None:
            return "", ""

        return self._severity_presenter.emoji(worst), "\n".join(f.message for f in findings)

    def _build_diagnosis_banner(self, song_index: int) -> QLabel | None:
        """A coloured banner atop the song detail listing its findings. Colours
        live in music_workshop.qss (keyed on the `severity` property); the
        heading comes from the shared SeverityPresenter."""
        findings = self._song_findings(song_index)
        worst = self._worst_severity(findings)
        if worst is None or self._severity_presenter is None:
            return None

        banner = QLabel()
        banner.setObjectName("workshopDiagBanner")
        banner.setProperty("severity", self._severity_presenter.css_class(worst))
        banner.setWordWrap(True)
        heading = escape(self._severity_presenter.heading(worst))
        messages = "<br>".join(escape(f.message) for f in findings)
        banner.setText(f"<b>{heading}</b><br>{messages}")
        return banner

    def _build_song_header(self, cseq: CseqFile) -> QWidget:
        first = cseq.songs[0] if cseq.songs else None
        bpm = first.bpm if first else 0
        tpqn = first.tpqn if first else 0
        track_count = len(first.tracks) if first else 0
        drum_indices = [i for i, t in enumerate(first.tracks) if t.is_drum] if first else []
        seq_count = len(cseq.songs)

        cards = [
            ("🎵", "TEMPO", str(bpm), "BPM"),
            ("⏱️", "RESOLUTION", str(tpqn), "ticks per quarter"),
            ("🎚", "TRACKS", str(track_count), self._tracks_hint(drum_indices)),
            ("🎼", "SEQUENCES",
                str(seq_count),
                "sub-song" if seq_count == 1 else "sub-songs",
             ),
            ("🎹", "INSTRUMENTS", str(len(cseq.instruments)), "melodic"),
            ("🥁", "PERCUSSION", str(len(cseq.percussions)), "drum samples"),
        ]

        bar = QFrame()
        bar.setObjectName("workshopStats")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for icon, label, value, hint in cards:
            layout.addWidget(self._build_stat_card(icon, label, value, hint), stretch=1)

        return bar

    def _tracks_hint(self, drum_indices: list[int]) -> str:
        if not drum_indices:
            return "no drum tracks"

        listing = ", ".join(str(i) for i in drum_indices)
        return f"drum: {listing}"

    def _build_stat_card(self, icon: str, label: str, value: str, hint: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("workshopStatCell")

        col = QVBoxLayout(frame)
        col.setContentsMargins(10, 8, 12, 8)
        col.setSpacing(2)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setObjectName("workshopStatIcon")
        header_row.addWidget(icon_label)

        label_widget = QLabel(label)
        label_widget.setObjectName("workshopStatLabel")
        label_widget.setAlignment(Qt.AlignVCenter)
        header_row.addWidget(label_widget, stretch=1)

        col.addLayout(header_row)

        value_widget = QLabel(value)
        value_widget.setObjectName("workshopStatValue")
        col.addWidget(value_widget)

        hint_widget = QLabel(hint)
        hint_widget.setObjectName("workshopStatHint")
        col.addWidget(hint_widget)

        return frame

    def _build_sequences_section(self, song_index: int, cseq: CseqFile) -> QWidget:
        """One row per sub-sequence with Play / Replace / Copy / Export /
        Remove buttons. Always rendered so single-sequence songs reach
        playback the same way as multi-sequence ones."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        heading = QLabel(f"Sequences ({len(cseq.songs)})")
        heading.setObjectName("workshopSectionLabel")
        layout.addWidget(heading)

        table = self._make_table(["#", "BPM", "Tracks", "Drum tracks", ""])

        for i, seq in enumerate(cseq.songs):
            drum_indices = [t_idx for t_idx, t in enumerate(seq.tracks) if t.is_drum]
            drum_text = ", ".join(str(idx) for idx in drum_indices) if drum_indices else "—"

            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, self._readonly_item(str(i)))
            table.setItem(row, 1, self._readonly_item(str(seq.bpm)))
            table.setItem(row, 2, self._readonly_item(str(len(seq.tracks))))
            table.setItem(row, 3, self._readonly_item(drum_text))
            table.setCellWidget(row, 4, self._build_sequence_actions(song_index, i))

        self._size_table(table)
        layout.addWidget(table)
        return section

    def _build_sequence_actions(self, song_index: int, seq_index: int) -> QWidget:
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        play = QPushButton("▶️")
        play.setObjectName("workshopRowButton")
        play.setToolTip("Render and play this sub-sequence")
        play.clicked.connect(
            lambda: self.sig_play_sequence.emit(song_index, seq_index),
        )
        layout.addWidget(play)

        menu = QMenu(wrap)
        menu.addAction(
            "🔄  Replace…",
            lambda: self.sig_replace_sequence.emit(song_index, seq_index),
        )
        menu.addAction(
            "📋  Copy to song…",
            lambda: self.sig_copy_sequence.emit(song_index, seq_index),
        )
        menu.addAction(
            "💾  Export as MIDI…",
            lambda: self.sig_export_sequence.emit(
                song_index, seq_index, f"Song {song_index} Sequence {seq_index}",
            ),
        )
        menu.addAction(
            "🔍  Inspect events",
            lambda: self.sig_view_sequence_events.emit(song_index, seq_index),
        )
        menu.addSeparator()
        menu.addAction(
            "🗑️  Remove",
            lambda: self.sig_remove_sequence.emit(song_index, seq_index),
        )

        layout.addWidget(self._build_actions_menu_button(menu))
        layout.addStretch(1)
        return wrap

    def _build_instruments_section(
        self, song_index: int, instruments: list[CseqInstrument],
    ) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        heading = QLabel(f"Instruments ({len(instruments)})")
        heading.setObjectName("workshopSectionLabel")
        layout.addWidget(heading)

        if not instruments:
            layout.addWidget(self._build_empty_label("No melodic instruments in this song."))
            return section

        table = self._make_table(
            ["#", "Sample", "Source bank", "Pitch", "Volume", "ADSR", ""],
        )

        for i, inst in enumerate(instruments):
            target = self._resolve_sample_target(inst.sample_id, f"Instrument {i}")
            row = table.rowCount()
            table.insertRow(row)

            table.setItem(row, 0, self._readonly_item(str(i)))
            table.setItem(row, 1, self._readonly_item(f"SPU #{inst.sample_id}"))
            table.setItem(row, 2, self._readonly_item(self._bank_label(target.bank_index)))
            table.setItem(row, 3, self._readonly_item(
                f"{inst.freq_hz} Hz ({self._pitch_to_note(inst.freq_hz)})",
            ))
            table.setItem(row, 4, self._readonly_item(f"{inst.volume}/255"))
            table.setItem(row, 5, self._readonly_item(f"0x{inst.adsr:08X}"))
            table.setCellWidget(row, 6, self._build_row_actions(
                target, inst.frequency,
                edit_callback=lambda s=song_index, idx=i: self.sig_edit_instrument.emit(s, idx),
                retarget_callback=lambda s=song_index, idx=i: self.sig_retarget_instrument.emit(s, idx),
            ))

        self._size_table(table)
        layout.addWidget(table)
        return section

    def _build_percussion_section(
        self, song_index: int, percussions: list[CseqPercussion],
    ) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        heading = QLabel(f"Percussion ({len(percussions)})")
        heading.setObjectName("workshopSectionLabel")
        layout.addWidget(heading)

        if not percussions:
            layout.addWidget(self._build_empty_label("No percussion in this song."))
            return section

        table = self._make_table(
            ["MIDI Note", "Drum name", "Sample", "Source bank", "Pitch", ""],
        )

        for i, perc in enumerate(percussions):
            midi_note = self._percussion_note_for_index(i)
            drum_name = self._drum_names.get_label(midi_note)
            target = self._resolve_sample_target(perc.sample_id, drum_name)
            row = table.rowCount()
            table.insertRow(row)

            table.setItem(row, 0, self._readonly_item(str(midi_note)))
            table.setItem(row, 1, self._readonly_item(drum_name))
            table.setItem(row, 2, self._readonly_item(f"SPU #{perc.sample_id}"))
            table.setItem(row, 3, self._readonly_item(self._bank_label(target.bank_index)))
            table.setItem(row, 4, self._readonly_item(f"{perc.freq_hz} Hz"))
            table.setCellWidget(row, 5, self._build_row_actions(
                target, perc.frequency,
                edit_callback=lambda s=song_index, idx=i: self.sig_edit_percussion.emit(s, idx),
                retarget_callback=lambda s=song_index, idx=i: self.sig_retarget_percussion.emit(s, idx),
            ))

        self._size_table(table)
        layout.addWidget(table)
        return section

    def _build_row_actions(
        self, target: SampleActionTarget, pitch: int,
        edit_callback=None, retarget_callback=None,
    ) -> QWidget:
        wrap = QWidget()
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        play = QPushButton("▶️")
        play.setObjectName("workshopRowButton")
        play.setToolTip("Audition this sample")
        play.clicked.connect(
            lambda: self.sig_play_instrument.emit(target.spu_index, pitch, target.label),
        )
        layout.addWidget(play)

        menu = QMenu(wrap)

        if edit_callback is not None:
            menu.addAction("✏️  Edit volume / pitch…", edit_callback)

        if retarget_callback is not None:
            menu.addAction("🎯  Point at another sample…", retarget_callback)

        if target.bank_index is not None and target.sample_index is not None:
            if not menu.isEmpty():
                menu.addSeparator()

            menu.addAction(
                "🔄  Replace sample (.vag)…",
                lambda: self.sig_replace_sample.emit(target.bank_index, target.sample_index),
            )
            menu.addAction(
                "📋  Copy sample to bank…",
                lambda: self.sig_copy_sample.emit(target.bank_index, target.sample_index),
            )
            menu.addAction(
                "💾  Export sample…",
                lambda: self.sig_export_sample.emit(target.bank_index, target.sample_index),
            )

        if not menu.isEmpty():
            layout.addWidget(self._build_actions_menu_button(menu))

        layout.addStretch(1)
        return wrap

    def _build_actions_menu_button(self, menu: QMenu) -> QPushButton:
        """Single ⚙️ button hosting all per-row non-play actions, matching
        the Category Browser's LeafRowWidget pattern. Fixed-width because
        Qt's menu indicator otherwise crops the emoji on narrow buttons."""
        button = QPushButton("⚙️")
        button.setObjectName("workshopRowButton")
        button.setToolTip("Actions")
        button.setFixedWidth(ButtonWidth.LEAF_ACTIONS)
        button.setMenu(menu)
        return button

    def _resolve_sample_target(self, spu_index: int, label: str) -> SampleActionTarget:
        if self._hwl is None:
            return SampleActionTarget(spu_index, None, None, label)

        location = self._sample_lookup.find_bank_and_sample_index(self._hwl, spu_index)
        bank_index, sample_index = location if location else (None, None)
        return SampleActionTarget(spu_index, bank_index, sample_index, label)

    def _bank_label(self, bank_index: int | None) -> str:
        if bank_index is None:
            return "— (not in any bank)"

        # Cross-reference into the bank reader to get the stock name, mirroring
        # the convention used elsewhere (file browser, copy dialog).
        try:
            name = self._sample_lookup._bank_reader.get_name(bank_index)
        except Exception:
            name = ""

        return f"Bank {bank_index} — {name}" if name else f"Bank {bank_index}"

    def _percussion_note_for_index(self, percussion_index: int) -> int:
        # CTR drum tracks reuse the MIDI note number directly as the percussion
        # table index (no remapping). Indices below the GM percussion key
        # range (27) still produce a sensible "Note N" label via
        # DrumNameResolver's fallback.
        return percussion_index

    def _pitch_to_note(self, hz: int) -> str:
        # Rough A4=440 mapping for a human-readable hint on the instrument's
        # base pitch. Not used for playback — just visual orientation.
        if hz <= 0:
            return "—"

        import math
        midi = 69 + 12 * math.log2(hz / 440.0)
        midi_round = int(round(midi))
        cents = int(round((midi - midi_round) * 100))
        name = _NOTE_NAMES[midi_round % 12]
        octave = midi_round // 12 - 1
        sign = "+" if cents >= 0 else ""
        return f"{name}{octave} {sign}{cents}¢"

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setObjectName("workshopTable")
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setShowGrid(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.Stretch)
        return table

    @staticmethod
    def _size_table(table: QTableWidget) -> None:
        table.resizeRowsToContents()
        # Lock height to the natural row count so each table flows in the
        # parent scroll area instead of carrying its own scrollbar.
        total = table.horizontalHeader().height()
        for row in range(table.rowCount()):
            total += table.rowHeight(row)

        table.setMinimumHeight(total + 2)
        table.setMaximumHeight(total + 2)

    @staticmethod
    def _readonly_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _build_empty_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("workshopEmpty")
        label.setAlignment(Qt.AlignCenter)
        return label

    def _show_empty_detail(self) -> None:
        self._clear_detail()
        empty = QLabel("Open a HWL file to see its songs here.")
        empty.setObjectName("workshopEmpty")
        empty.setAlignment(Qt.AlignCenter)
        self._detail_layout.addWidget(empty)
        self._detail_layout.addStretch(1)

    def _render_error(self, message: str) -> None:
        self._clear_detail()
        label = QLabel(message)
        label.setObjectName("workshopEmpty")
        label.setAlignment(Qt.AlignCenter)
        self._detail_layout.addWidget(label)
        self._detail_layout.addStretch(1)

    def _clear_detail(self) -> None:
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            w = item.widget()

            if w is not None:
                w.deleteLater()
