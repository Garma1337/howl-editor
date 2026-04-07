# coding: utf-8

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QSplitter, QTextEdit, QWidget, QVBoxLayout, QMenu, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QHeaderView, QAbstractItemView,
)

from howl_editor.analysis import SampleClassifier, BankCseqValidator
from howl_editor.audio.audio_player import AudioPlayer
from howl_editor.audio.cseq_renderer import CseqRenderer
from howl_editor.audio.decoder.vag_decoder import VagDecoder
from howl_editor.bank import BankReader, BankBuilder
from howl_editor.cseq import CseqReader, CseqWriter
from howl_editor.cseq.editor import CseqEditor
from howl_editor.export import BatchExporter
from howl_editor.gui.detail.detail_formatter import DetailFormatter
from howl_editor.gui.handler.bank_handler import BankHandler
from howl_editor.gui.handler.playback_handler import PlaybackHandler
from howl_editor.gui.handler.sample_handler import SampleHandler
from howl_editor.gui.handler.song_handler import SongHandler
from howl_editor.gui.handler.tools_handler import ToolsHandler
from howl_editor.gui.widget import FilterWidget, PlayerWidget, WaveformWidget
from howl_editor.howl import HowlReader, HowlWriter, HowlEditor
from howl_editor.howl.version import HowlVersionDetector
from howl_editor.midi.converter import MidiConverter, HAS_MIDO
from howl_editor.midi.exporter import CseqMidiExporter
from howl_editor.models import HowlFile
from howl_editor.vag import VagReader, VagWriter

NODE_ROOT = 0
NODE_SPU_TABLE = 1
NODE_EFFECTS = 2
NODE_ENGINE_FX = 3
NODE_BANKS = 4
NODE_BANK = 5
NODE_SONGS = 6
NODE_SONG = 7
NODE_SAMPLE = 8
NODE_SEQUENCE = 9
NODE_OTHER_FX_ENTRY = 10
NODE_ENGINE_FX_ENTRY = 11


class MainWindow(QMainWindow):

    def __init__(
        self,
        howl_reader: HowlReader | None = None,
        howl_writer: HowlWriter | None = None,
        howl_editor_svc: HowlEditor | None = None,
        cseq_reader: CseqReader | None = None,
        cseq_writer: CseqWriter | None = None,
        cseq_editor: CseqEditor | None = None,
        vag_reader: VagReader | None = None,
        vag_writer: VagWriter | None = None,
        bank_reader: BankReader | None = None,
        bank_builder: BankBuilder | None = None,
        midi_converter: MidiConverter | None = None,
        midi_exporter: CseqMidiExporter | None = None,
        vag_decoder: VagDecoder | None = None,
        cseq_renderer: CseqRenderer | None = None,
        audio_player: AudioPlayer | None = None,
        version_detector: HowlVersionDetector | None = None,
        sample_classifier: SampleClassifier | None = None,
        validator: BankCseqValidator | None = None,
        batch_exporter: BatchExporter | None = None,
        detail_formatter: DetailFormatter | None = None,
    ):
        super().__init__()
        self.setWindowTitle("HOWL Editor")
        self.resize(1100, 700)

        self._reader = howl_reader
        self._writer = howl_writer
        self._editor = howl_editor_svc
        self._cseq_reader = cseq_reader
        self._cseq_writer = cseq_writer
        self._cseq_editor = cseq_editor
        self._vag_reader = vag_reader
        self._vag_writer = vag_writer
        self._bank_reader = bank_reader
        self._bank_builder = bank_builder
        self._midi_converter = midi_converter
        self._midi_exporter = midi_exporter
        self._vag_decoder = vag_decoder
        self._cseq_renderer = cseq_renderer
        self._audio_player = audio_player
        self._version_detector = version_detector
        self._sample_classifier = sample_classifier
        self._validator = validator
        self._batch_exporter = batch_exporter
        self._detail_fmt = detail_formatter
        self._sample_types: dict[int, set] = {}

        self.hwl: HowlFile | None = None
        self.file_path: str | None = None
        self.modified = False
        self._file_actions: list[QAction] = []

        self._bank_handler = BankHandler(self)
        self._sample_handler = SampleHandler(self)
        self._song_handler = SongHandler(self)
        self._playback = PlaybackHandler(self)
        self._tools = ToolsHandler(self)

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: filter bar + tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.filter_widget = FilterWidget()
        left_layout.addWidget(self.filter_widget)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Info"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.currentItemChanged.connect(self._on_selection_changed)
        self.tree.itemClicked.connect(self._on_item_clicked)

        # Drag-and-drop for reordering banks, songs, and sequences
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.model().rowsMoved.connect(self._on_rows_moved)

        left_layout.addWidget(self.tree)
        self.filter_widget.set_tree(self.tree)

        # Right panel: detail view + waveform + audio transport
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        right_layout.addWidget(self.details, stretch=1)

        self.waveform = WaveformWidget()
        self.waveform.setVisible(False)
        right_layout.addWidget(self.waveform)

        self.player_widget = PlayerWidget()
        right_layout.addWidget(self.player_widget)

        if self._audio_player and self._audio_player.media_player:
            self.player_widget.connect_player(
                self._audio_player.media_player, self._playback.stop,
            )

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([660, 440])
        self.setCentralWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready - Open or create a new HWL file")

    def _setup_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&New", self._new_file, QKeySequence.New)
        self._add_action(file_menu, "&Open...", self._open_file, QKeySequence.Open)
        self._add_action(file_menu, "&Close", self._close_file, QKeySequence.Close, requires_file=True)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self._save_file, QKeySequence.Save, requires_file=True)
        self._add_action(file_menu, "Save &As...", self._save_file_as, QKeySequence("Ctrl+Shift+S"), requires_file=True)
        file_menu.addSeparator()
        self._add_action(file_menu, "Batch &Export...", self._tools.batch_export, requires_file=True)
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, QKeySequence.Quit)

        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "Add &Bank...", self._bank_handler.add_bank, requires_file=True)
        self._add_action(edit_menu, "Add &Song...", self._song_handler.add_song, requires_file=True)

        tools_menu = menubar.addMenu("&Tools")
        self._add_action(tools_menu, "Build Bank from &VAGs...", self._tools.build_bank_from_vags)
        midi_text = "&Convert MIDI to CSEQ..." if HAS_MIDO else "Convert MIDI to CSEQ (mido not installed)"
        self._add_action(tools_menu, midi_text, self._tools.midi_to_cseq, enabled=HAS_MIDO)
        self._add_action(tools_menu, "&Validate Bank/Song...", self._tools.validate_bank_song, requires_file=True)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Clear Audio &Cache", self._clear_audio_cache)

    def _add_action(self, menu, text, slot, shortcut=None, enabled=True, requires_file=False):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)

        action.triggered.connect(slot)
        menu.addAction(action)

        if requires_file:
            action.setEnabled(False)
            self._file_actions.append(action)
        else:
            action.setEnabled(enabled)

        return action

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("New", self._new_file)
        toolbar.addAction("Open", self._open_file)
        self._file_actions.append(toolbar.addAction("Close", self._close_file))
        self._file_actions.append(toolbar.addAction("Save", self._save_file))
        toolbar.addSeparator()
        self._file_actions.append(toolbar.addAction("Add Bank", self._bank_handler.add_bank))
        self._file_actions.append(toolbar.addAction("Add Song", self._song_handler.add_song))
        toolbar.addSeparator()
        self._file_actions.append(toolbar.addAction("Stop Playback", self._playback.stop))

        for action in self._file_actions:
            action.setEnabled(False)

    def _clear_audio_cache(self):
        if self._audio_player:
            self._audio_player.stop()
            count = self._audio_player.clear_cache()
            self.status.showMessage(f"Cleared {count} cached audio file(s)")

    def _close_file(self):
        if not self._check_unsaved():
            return

        if self._audio_player:
            self._audio_player.stop()

        self.hwl = None
        self.file_path = None
        self.modified = False
        self._sample_types = {}
        self.tree.clear()
        self.details.clear()
        self.waveform.clear()
        self.waveform.setVisible(False)
        self.player_widget.clear()
        self.filter_widget.reset()
        self._set_file_actions_enabled(False)
        self.status.showMessage("Ready - Open or create a new HWL file")
        self._update_title()

    def _new_file(self):
        if not self._check_unsaved():
            return

        self.hwl = HowlFile()
        self.file_path = None
        self.modified = False
        self._rebuild_tree()
        self._set_file_actions_enabled(True)
        self.status.showMessage("New HWL file created")
        self._update_title()

    def _open_file(self):
        if not self._check_unsaved():
            return

        path, _ = QFileDialog.getOpenFileName(self, "Open HWL File", "", "HWL Files (*.hwl);;All Files (*)")
        if not path:
            return

        try:
            self.hwl = self._reader.read_file(path)
            self.file_path = path
            self.modified = False
            self._rebuild_tree()
            self._set_file_actions_enabled(True)
            self.status.showMessage(f"Loaded: {path} ({len(self.hwl.banks)} banks, {len(self.hwl.songs)} songs)")
            self._update_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open HWL:\n{e}")

    def _save_file(self):
        if not self.hwl:
            return

        if not self.file_path:
            self._save_file_as()
            return

        try:
            self._writer.write_file(self.hwl, self.file_path)
            self.modified = False
            self.status.showMessage(f"Saved: {self.file_path}")
            self._update_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def _save_file_as(self):
        if not self.hwl:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save HWL File", "", "HWL Files (*.hwl);;All Files (*)")
        if path:
            self.file_path = path
            self._save_file()

    def _check_unsaved(self) -> bool:
        if not self.modified:
            return True

        return QMessageBox.question(
            self, "Unsaved Changes", "There are unsaved changes. Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes

    def _update_title(self):
        parts = ["HOWL Editor"]
        if self.file_path:
            parts.append(Path(self.file_path).name)

        title = " - ".join(parts)
        if self.modified:
            title += " *"

        self.setWindowTitle(title)

    def _notify(self, message: str) -> None:
        self.status.showMessage(message)
        QMessageBox.information(self, "HOWL Editor", message)

    def _set_file_actions_enabled(self, enabled: bool):
        for action in self._file_actions:
            action.setEnabled(enabled)

    def _mark_modified(self):
        self.modified = True
        self._update_title()

    def _save_tree_state(self) -> tuple[set[str], str | None]:
        expanded: set[str] = set()
        selected_path: str | None = None

        current = self.tree.currentItem()
        if current:
            selected_path = self._get_item_path(current)

        iterator = QTreeWidgetItemIterator(self.tree)

        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                expanded.add(self._get_item_path(item))

            iterator += 1

        return expanded, selected_path

    def _restore_tree_state(self, expanded: set[str], selected_path: str | None) -> None:
        if not expanded and not selected_path:
            return

        self.tree.blockSignals(True)

        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            path = self._get_item_path(item)
            item.setExpanded(path in expanded)

            if path == selected_path:
                self.tree.setCurrentItem(item)

            iterator += 1

        self.tree.blockSignals(False)

    def _get_item_path(self, item) -> str:
        parts = []

        while item:
            node_type = item.data(0, Qt.UserRole)
            index = item.data(0, Qt.UserRole + 1)
            sub_index = item.data(0, Qt.UserRole + 2)
            key = str(node_type)

            if index is not None:
                key += f".{index}"

            if sub_index is not None:
                key += f".{sub_index}"

            parts.append(key)
            item = item.parent()

        return "/".join(reversed(parts))

    def _rebuild_tree(self):
        expanded, selected_path = self._save_tree_state()

        self.tree.clear()
        self.details.clear()

        if not self.hwl:
            return

        if self._sample_classifier:
            self._sample_types = self._sample_classifier.classify(self.hwl)
        else:
            self._sample_types = {}

        root = self._tree_item(None, f"HOWL (v{self.hwl.version})", f"{len(self.hwl.banks)} banks, {len(self.hwl.songs)} songs", NODE_ROOT)
        root.setExpanded(True)

        self._tree_item(root, "SPU Address Table", f"{len(self.hwl.spu_addrs)} entries", NODE_SPU_TABLE)

        fx_node = self._tree_item(root, "Effects (OtherFX)", f"{len(self.hwl.other_fx)} entries", NODE_EFFECTS)
        for i, fx in enumerate(self.hwl.other_fx):
            self._tree_item(fx_node, f"FX {i} (SPU {fx.spu_index})", f"vol={fx.volume}, pitch={fx.pitch}, dur={fx.duration}", NODE_OTHER_FX_ENTRY, i)

        engine_node = self._tree_item(root, "Engine FX", f"{len(self.hwl.engine_fx)} entries", NODE_ENGINE_FX)
        for i, fx in enumerate(self.hwl.engine_fx):
            self._tree_item(engine_node, f"Engine {i} (SPU {fx.spu_index})", f"vol={fx.volume}, pitch={fx.pitch}", NODE_ENGINE_FX_ENTRY, i)

        banks_node = self._tree_item(root, "Banks", str(len(self.hwl.banks)), NODE_BANKS)
        banks_node.setExpanded(True)

        for i, bank in enumerate(self.hwl.banks):
            info = self._detail_fmt.bank.format_tree_info(bank)
            label = self._get_item_label("Bank", i, self._bank_reader.get_name(i))
            bank_node = self._tree_item(banks_node, label, info, NODE_BANK, i)
            self._populate_bank_samples(bank_node, i)

        songs_node = self._tree_item(root, "Songs", str(len(self.hwl.songs)), NODE_SONGS)
        songs_node.setExpanded(True)

        for i, song in enumerate(self.hwl.songs):
            info = self._detail_fmt.song.format_tree_info(song)
            label = self._get_item_label("Song", i, self._cseq_reader.get_name(i))
            song_node = self._tree_item(songs_node, label, info, NODE_SONG, i)
            self._populate_song_sequences(song_node, i)

        self._restore_tree_state(expanded, selected_path)

    def _get_item_label(self, prefix: str, index: int, name: str) -> str:
        if name:
            return f"{prefix} {index} - {name}"

        return f"{prefix} {index}"

    def _tree_item(self, parent, text, info, node_type, index=None, sub_index=None):
        item = QTreeWidgetItem(parent or self.tree, [text, info])
        item.setData(0, Qt.UserRole, node_type)

        if index is not None:
            item.setData(0, Qt.UserRole + 1, index)

        if sub_index is not None:
            item.setData(0, Qt.UserRole + 2, sub_index)

        return item

    def _populate_bank_samples(self, bank_node, bank_index: int) -> None:
        try:
            samples = self._bank_reader.parse(self.hwl.banks[bank_index], self.hwl.spu_addrs)

            for j, sample in enumerate(samples):
                types = self._sample_types.get(sample.spu_index, set())
                type_label = self._sample_classifier.get_label(types) if self._sample_classifier and types else ""
                label = f"SPU {sample.spu_index}"
                parts = [f"{len(sample.data):,} bytes"]

                if type_label:
                    parts.append(type_label)

                self._tree_item(bank_node, label, ", ".join(parts), NODE_SAMPLE, bank_index, j)
        except Exception:
            pass

    def _populate_song_sequences(self, song_node, song_index: int) -> None:
        try:
            cseq = self._cseq_reader.read(self.hwl.songs[song_index])

            for j, seq in enumerate(cseq.songs):
                label = f"Sequence {j}"
                info = f"BPM={seq.bpm}, {len(seq.tracks)} tracks"
                self._tree_item(song_node, label, info, NODE_SEQUENCE, song_index, j)
        except Exception:
            pass

    def _on_selection_changed(self, current):
        if not current or not self.hwl:
            self.details.clear()
            self.waveform.setVisible(False)
            return

        node_type = current.data(0, Qt.UserRole)
        index = current.data(0, Qt.UserRole + 1)
        sub_index = current.data(0, Qt.UserRole + 2)

        formatters = {
            NODE_ROOT: lambda: self._detail_fmt.howl.format_details(self.hwl, self.file_path),
            NODE_SPU_TABLE: lambda: self._detail_fmt.howl.format_spu_table(self.hwl),
            NODE_EFFECTS: lambda: self._detail_fmt.fx.format_effects_table(self.hwl),
            NODE_ENGINE_FX: lambda: self._detail_fmt.fx.format_engine_fx_table(self.hwl),
            NODE_OTHER_FX_ENTRY: lambda: self._detail_fmt.fx.format_other_fx_details(self.hwl, index),
            NODE_ENGINE_FX_ENTRY: lambda: self._detail_fmt.fx.format_engine_fx_details(self.hwl, index),
            NODE_BANKS: lambda: self._detail_fmt.bank.format_summary(self.hwl),
            NODE_BANK: lambda: self._detail_fmt.bank.format_details(self.hwl, index),
            NODE_SONGS: lambda: self._detail_fmt.song.format_summary(self.hwl),
            NODE_SONG: lambda: self._detail_fmt.song.format_details(self.hwl, index),
        }

        # Waveform on selection: samples and FX entries (instant decode)
        if node_type == NODE_SAMPLE and index is not None and sub_index is not None:
            self._show_sample_waveform(index, sub_index)
        elif node_type == NODE_OTHER_FX_ENTRY and index is not None:
            self._show_fx_waveform(self.hwl.other_fx[index].spu_index)
        elif node_type == NODE_ENGINE_FX_ENTRY and index is not None:
            self._show_fx_waveform(self.hwl.engine_fx[index].spu_index)
        else:
            self.waveform.setVisible(False)

        fn = formatters.get(node_type)
        if fn:
            self.details.setHtml(fn())

    def _show_sample_waveform(self, bank_index: int, sample_index: int) -> None:
        type_labeler = self._sample_classifier.get_label if self._sample_classifier else None
        self.details.setHtml(self._detail_fmt.bank.format_sample_details(
            self.hwl, bank_index, sample_index, self._sample_types, type_labeler,
        ))

        try:
            samples = self._bank_reader.parse(self.hwl.banks[bank_index], self.hwl.spu_addrs)

            if sample_index < len(samples):
                pcm, loop_start = self._vag_decoder.decode_with_loop(samples[sample_index].data)
                self.waveform.set_samples(pcm, loop_start)
                self.waveform.setVisible(True)
                return
        except Exception:
            pass

        self.waveform.setVisible(False)

    def _show_fx_waveform(self, spu_index: int) -> None:
        try:
            data = self._playback._find_sample_data(spu_index)

            if data:
                pcm, loop_start = self._vag_decoder.decode_with_loop(data)
                self.waveform.set_samples(pcm, loop_start)
                self.waveform.setVisible(True)
                return
        except Exception:
            pass

        self.waveform.setVisible(False)

    def _on_item_clicked(self, item):
        if not item or not self.hwl:
            return

        node_type = item.data(0, Qt.UserRole)
        index = item.data(0, Qt.UserRole + 1)
        sub_index = item.data(0, Qt.UserRole + 2)

        if node_type == NODE_SAMPLE and index is not None and sub_index is not None:
            self._playback.play_sample(index, sub_index)
        elif node_type == NODE_SEQUENCE and index is not None and sub_index is not None:
            self._playback.play_sequence(index, sub_index)
        elif node_type == NODE_OTHER_FX_ENTRY and index is not None:
            self._playback.play_other_fx(index)
        elif node_type == NODE_ENGINE_FX_ENTRY and index is not None:
            self._playback.play_engine_fx(index)

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item or not self.hwl:
            return

        node_type = item.data(0, Qt.UserRole)
        index = item.data(0, Qt.UserRole + 1)
        sub_index = item.data(0, Qt.UserRole + 2)

        menu = QMenu(self)
        if node_type == NODE_SAMPLE and index is not None and sub_index is not None:
            menu.addAction("Export as VAG...", lambda: self._sample_handler.export_sample(index, sub_index))
            menu.addAction("Export as WAV...", lambda: self._sample_handler.export_sample_as_wav(index, sub_index))
            menu.addSeparator()
            menu.addAction("Replace Sample (.vag)...", lambda: self._sample_handler.replace_sample(index, sub_index))
            menu.addAction("Remove Sample", lambda: self._sample_handler.remove_sample(index, sub_index))
        elif node_type == NODE_BANK and index is not None:
            menu.addAction("Export Bank (.bnk)...", lambda: self._bank_handler.export_bank(index))
            menu.addAction("Export Samples as VAGs...", lambda: self._bank_handler.export_bank_samples(index))
            menu.addAction("Export Samples as WAVs...", lambda: self._bank_handler.export_bank_samples_as_wav(index))
            menu.addSeparator()

            if index > 0:
                menu.addAction("Move Up", lambda: self._move_bank(index, index - 1))
            if index < len(self.hwl.banks) - 1:
                menu.addAction("Move Down", lambda: self._move_bank(index, index + 1))

            menu.addSeparator()
            menu.addAction("Add Sample (.vag)...", lambda: self._sample_handler.add_sample(index))
            menu.addAction("Merge Bank...", lambda: self._bank_handler.merge_bank(index))
            menu.addAction("Replace Bank...", lambda: self._bank_handler.replace_bank(index))
            menu.addAction("Remove Bank", lambda: self._bank_handler.remove_bank(index))
        elif node_type == NODE_SEQUENCE and index is not None and sub_index is not None:
            menu.addAction("Export as MIDI...", lambda: self._song_handler.export_sequence_as_midi(index, sub_index))
            menu.addSeparator()

            try:
                cseq = self._cseq_reader.read(self.hwl.songs[index])
                seq_count = len(cseq.songs)
            except Exception:
                seq_count = 0

            if sub_index > 0:
                menu.addAction("Move Up", lambda: self._move_sequence(index, sub_index, sub_index - 1))
            if seq_count > 0 and sub_index < seq_count - 1:
                menu.addAction("Move Down", lambda: self._move_sequence(index, sub_index, sub_index + 1))

            menu.addSeparator()
            menu.addAction("Replace Sequence...", lambda: self._song_handler.replace_sequence(index, sub_index))
            menu.addAction("Remove Sequence", lambda: self._song_handler.remove_sequence(index, sub_index))
        elif node_type == NODE_SONG and index is not None:
            menu.addAction("Export Song (.cseq)...", lambda: self._song_handler.export_song(index))
            menu.addAction("Export as MIDI...", lambda: self._song_handler.export_song_as_midi(index))
            menu.addSeparator()

            if index > 0:
                menu.addAction("Move Up", lambda: self._move_song(index, index - 1))
            if index < len(self.hwl.songs) - 1:
                menu.addAction("Move Down", lambda: self._move_song(index, index + 1))

            menu.addSeparator()
            menu.addAction("Replace Song...", lambda: self._song_handler.replace_song(index))
            menu.addAction("Remove Song", lambda: self._song_handler.remove_song(index))
        elif node_type == NODE_BANKS:
            menu.addAction("Add Bank from File...", self._bank_handler.add_bank)
            menu.addAction("Build Bank from VAGs...", self._tools.build_bank_from_vags)
        elif node_type == NODE_SONGS:
            menu.addAction("Add Song from File...", self._song_handler.add_song)
            if HAS_MIDO:
                menu.addAction("Add Song from MIDI...", self._tools.midi_to_cseq)
        else:
            return

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _move_bank(self, from_index: int, to_index: int) -> None:
        try:
            self._editor.move_bank(self.hwl, from_index, to_index)
            self._mark_modified()
            self._rebuild_tree()
            self.status.showMessage(f"Moved bank {from_index} to position {to_index}")
        except Exception as e:
            self.status.showMessage(f"Move failed: {e}")

    def _move_song(self, from_index: int, to_index: int) -> None:
        try:
            self._editor.move_song(self.hwl, from_index, to_index)
            self._mark_modified()
            self._rebuild_tree()
            self.status.showMessage(f"Moved song {from_index} to position {to_index}")
        except Exception as e:
            self.status.showMessage(f"Move failed: {e}")

    def _move_sequence(self, song_index: int, from_index: int, to_index: int) -> None:
        try:
            self.hwl.songs[song_index] = self._cseq_editor.move_sequence(
                self.hwl.songs[song_index], from_index, to_index,
            )
            self._mark_modified()
            self._rebuild_tree()
            self.status.showMessage(f"Moved sequence {from_index} to position {to_index}")
        except Exception as e:
            self.status.showMessage(f"Move failed: {e}")

    def _on_rows_moved(self, start, destination, dest_row):
        """Handle drag-and-drop reorder of banks, songs, or sequences."""
        if not self.hwl:
            return

        # Determine what was moved by checking the parent node type
        if destination.isValid():
            parent_item = self.tree.itemFromIndex(destination)
        else:
            parent_item = None

        if not parent_item:
            return

        parent_type = parent_item.data(0, Qt.UserRole)

        try:
            if parent_type == NODE_BANKS:
                self._editor.move_bank(self.hwl, start, dest_row if dest_row <= start else dest_row - 1)
                self._mark_modified()
                self._rebuild_tree()
                self.status.showMessage(f"Moved bank {start} to position {dest_row}")

            elif parent_type == NODE_SONGS:
                self._editor.move_song(self.hwl, start, dest_row if dest_row <= start else dest_row - 1)
                self._mark_modified()
                self._rebuild_tree()
                self.status.showMessage(f"Moved song {start} to position {dest_row}")

            elif parent_type == NODE_SONG:
                song_index = parent_item.data(0, Qt.UserRole + 1)
                if song_index is not None:
                    to_idx = dest_row if dest_row <= start else dest_row - 1

                    self.hwl.songs[song_index] = self._cseq_editor.move_sequence(
                        self.hwl.songs[song_index], start, to_idx,
                    )

                    self._mark_modified()
                    self._rebuild_tree()
                    self.status.showMessage(f"Moved sequence {start} to position {dest_row}")
        except (IndexError, Exception) as e:
            self.status.showMessage(f"Move failed: {e}")
            self._rebuild_tree()

    def closeEvent(self, event):
        if self._check_unsaved():
            event.accept()
        else:
            event.ignore()
