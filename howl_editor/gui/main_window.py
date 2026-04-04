# coding: utf-8

import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit,
    QMenu, QToolBar, QStatusBar, QFileDialog, QMessageBox, QDialog,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from howl_editor.models import HowlFile, VagSample
from howl_editor.howl import HowlReader, HowlWriter, HowlEditor
from howl_editor.cseq import CseqReader, CseqWriter
from howl_editor.vag import VagReader, VagWriter
from howl_editor.bank import BankReader, BankBuilder
from howl_editor.midi.converter import MidiConverter, HAS_MIDO
from howl_editor.gui.midi_dialog import MidiMappingDialog
from howl_editor.gui.detail_formatter import DetailFormatter


NODE_ROOT = 0
NODE_SPU_TABLE = 1
NODE_EFFECTS = 2
NODE_ENGINE_FX = 3
NODE_BANKS = 4
NODE_BANK = 5
NODE_SONGS = 6
NODE_SONG = 7


class MainWindow(QMainWindow):

    def __init__(
        self,
        howl_reader: HowlReader | None = None,
        howl_writer: HowlWriter | None = None,
        howl_editor_svc: HowlEditor | None = None,
        cseq_reader: CseqReader | None = None,
        cseq_writer: CseqWriter | None = None,
        vag_reader: VagReader | None = None,
        vag_writer: VagWriter | None = None,
        bank_reader: BankReader | None = None,
        bank_builder: BankBuilder | None = None,
        midi_converter: MidiConverter | None = None,
    ):
        super().__init__()
        self.setWindowTitle("HOWL Editor")
        self.resize(1100, 700)

        self._reader = howl_reader
        self._writer = howl_writer
        self._editor = howl_editor_svc
        self._cseq_reader = cseq_reader
        self._cseq_writer = cseq_writer
        self._vag_reader = vag_reader
        self._vag_writer = vag_writer
        self._bank_reader = bank_reader
        self._bank_builder = bank_builder
        self._midi_converter = midi_converter
        self._detail_fmt = DetailFormatter(self._cseq_reader)

        self.hwl: HowlFile | None = None
        self.file_path: str | None = None
        self.modified = False

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "Info"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.currentItemChanged.connect(self._on_selection_changed)

        self.details = QTextEdit()
        self.details.setReadOnly(True)

        splitter.addWidget(self.tree)
        splitter.addWidget(self.details)
        splitter.setSizes([450, 650])
        self.setCentralWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready - Open or create a new HWL file")

    def _setup_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&New", self._new_file, QKeySequence.New)
        self._add_action(file_menu, "&Open...", self._open_file, QKeySequence.Open)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self._save_file, QKeySequence.Save)
        self._add_action(file_menu, "Save &As...", self._save_file_as, QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, QKeySequence.Quit)

        edit_menu = menubar.addMenu("&Edit")
        self._add_action(edit_menu, "Add &Bank...", self._add_bank)
        self._add_action(edit_menu, "Add &Song...", self._add_song)

        tools_menu = menubar.addMenu("&Tools")
        self._add_action(tools_menu, "Build Bank from &VAGs...", self._build_bank_from_vags)
        midi_text = "&MIDI to CSEQ..." if HAS_MIDO else "MIDI to CSEQ (mido not installed)"
        self._add_action(tools_menu, midi_text, self._midi_to_cseq, enabled=HAS_MIDO)

    def _add_action(self, menu, text, slot, shortcut=None, enabled=True):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)

        action.setEnabled(enabled)
        action.triggered.connect(slot)
        menu.addAction(action)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        for label, slot in [("New", self._new_file), ("Open", self._open_file), ("Save", self._save_file)]:
            toolbar.addAction(label).triggered.connect(slot)
        
        toolbar.addSeparator()
        toolbar.addAction("Add Bank").triggered.connect(self._add_bank)
        toolbar.addAction("Add Song").triggered.connect(self._add_song)

    def _new_file(self):
        if not self._check_unsaved():
            return

        self.hwl = HowlFile()
        self.file_path = None
        self.modified = False
        self._rebuild_tree()
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
            self.status.showMessage(f"Loaded: {path} ({len(self.hwl.banks)} banks, {len(self.hwl.songs)} songs)")
            self._update_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open HWL:\n{e}")

    def _save_file(self):
        if not self.hwl:
            return

        if not self.file_path:
            return self._save_file_as()
        
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
        
        return QMessageBox.question(self, "Unsaved Changes", "There are unsaved changes. Continue?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def _update_title(self):
        parts = ["HOWL Editor"]
        if self.file_path:
            parts.append(Path(self.file_path).name)

        title = " - ".join(parts)
        
        if self.modified:
            title += " *"
        
        self.setWindowTitle(title)

    def _mark_modified(self):
        self.modified = True
        self._update_title()

    def _rebuild_tree(self):
        self.tree.clear()
        self.details.clear()

        if not self.hwl:
            return

        root = self._tree_item(None, f"HOWL (v{self.hwl.version})", f"{len(self.hwl.banks)} banks, {len(self.hwl.songs)} songs", NODE_ROOT)
        root.setExpanded(True)

        self._tree_item(root, "SPU Address Table", f"{len(self.hwl.spu_addrs)} entries", NODE_SPU_TABLE)
        self._tree_item(root, "Effects (OtherFX)", f"{len(self.hwl.other_fx)} entries", NODE_EFFECTS)
        self._tree_item(root, "Engine FX", f"{len(self.hwl.engine_fx)} entries", NODE_ENGINE_FX)

        banks_node = self._tree_item(root, "Banks", str(len(self.hwl.banks)), NODE_BANKS)
        banks_node.setExpanded(True)

        for i, bank in enumerate(self.hwl.banks):
            info = self._detail_fmt.bank_summary(bank)
            self._tree_item(banks_node, f"Bank {i}", info, NODE_BANK, i)

        songs_node = self._tree_item(root, "Songs", str(len(self.hwl.songs)), NODE_SONGS)
        songs_node.setExpanded(True)
        
        for i, song in enumerate(self.hwl.songs):
            info = self._detail_fmt.song_summary(song)
            self._tree_item(songs_node, f"Song {i}", info, NODE_SONG, i)

    def _tree_item(self, parent, text, info, node_type, index=None):
        item = QTreeWidgetItem(parent or self.tree, [text, info])
        item.setData(0, Qt.UserRole, node_type)
        
        if index is not None:
            item.setData(0, Qt.UserRole + 1, index)
        
        return item

    def _on_selection_changed(self, current, previous):
        if not current or not self.hwl:
            self.details.clear()
            return

        node_type = current.data(0, Qt.UserRole)
        index = current.data(0, Qt.UserRole + 1)

        formatters = {
            NODE_ROOT: lambda: self._detail_fmt.howl_details(self.hwl, self.file_path),
            NODE_SPU_TABLE: lambda: self._detail_fmt.spu_table(self.hwl),
            NODE_EFFECTS: lambda: self._detail_fmt.effects_table(self.hwl),
            NODE_ENGINE_FX: lambda: self._detail_fmt.engine_fx_table(self.hwl),
            NODE_BANKS: lambda: self._detail_fmt.banks_summary(self.hwl),
            NODE_BANK: lambda: self._detail_fmt.bank_details(self.hwl, index),
            NODE_SONGS: lambda: self._detail_fmt.songs_summary(self.hwl),
            NODE_SONG: lambda: self._detail_fmt.song_details(self.hwl, index),
        }

        fn = formatters.get(node_type)
        self.details.setPlainText(fn() if fn else "")

    def _on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item or not self.hwl:
            return

        node_type = item.data(0, Qt.UserRole)
        index = item.data(0, Qt.UserRole + 1)

        menu = QMenu(self)
        if node_type == NODE_BANK and index is not None:
            menu.addAction("Export Bank (.bnk)...", lambda: self._export_bank(index))
            menu.addAction("Export Samples as VAGs...", lambda: self._export_bank_samples(index))
            menu.addSeparator()
            menu.addAction("Replace Bank...", lambda: self._replace_bank(index))
            menu.addAction("Remove Bank", lambda: self._remove_bank(index))
        elif node_type == NODE_SONG and index is not None:
            menu.addAction("Export Song (.cseq)...", lambda: self._export_song(index))
            menu.addSeparator()
            menu.addAction("Replace Song...", lambda: self._replace_song(index))
            menu.addAction("Remove Song", lambda: self._remove_song(index))
        elif node_type == NODE_BANKS:
            menu.addAction("Add Bank from File...", self._add_bank)
            menu.addAction("Build Bank from VAGs...", self._build_bank_from_vags)
        elif node_type == NODE_SONGS:
            menu.addAction("Add Song from File...", self._add_song)
            if HAS_MIDO:
                menu.addAction("Add Song from MIDI...", self._midi_to_cseq)
        else:
            return

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _add_bank(self):
        if not self.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self, "Add Bank", "", "Bank Files (*.bnk);;All Files (*)")
        if not path:
            return
        
        self._editor.add_bank(self.hwl, Path(path).read_bytes())
        self._mark_modified()
        self._rebuild_tree()
        self.status.showMessage(f"Added bank from {Path(path).name}")

    def _export_bank(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self, f"Export Bank {index}", f"bank_{index}.bnk", "Bank Files (*.bnk)")
        
        if path:
            Path(path).write_bytes(self.hwl.banks[index])
            self.status.showMessage(f"Exported bank {index}")

    def _export_bank_samples(self, index: int):
        folder = QFileDialog.getExistingDirectory(self, f"Export Samples from Bank {index}")
        
        if not folder:
            return
        
        try:
            samples = self._bank_reader.parse(self.hwl.banks[index], self.hwl.spu_addrs)
            for sample in samples:
                self._vag_writer.write_file(
                    VagSample(data=sample.data),
                    Path(folder) / f"sample_{sample.spu_index}.vag",
                )
            
            self.status.showMessage(f"Exported {len(samples)} samples from bank {index}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")

    def _replace_bank(self, index: int):
        path, _ = QFileDialog.getOpenFileName(self, f"Replace Bank {index}", "", "Bank Files (*.bnk);;All Files (*)")
        if not path:
            return

        self._editor.replace_bank(self.hwl, index, Path(path).read_bytes())
        self._mark_modified()
        self._rebuild_tree()

    def _remove_bank(self, index: int):
        if QMessageBox.question(self, "Remove Bank", f"Remove bank {index}?") == QMessageBox.Yes:
            self._editor.remove_bank(self.hwl, index)
            self._mark_modified()
            self._rebuild_tree()

    def _add_song(self):
        if not self.hwl:
            return

        path, _ = QFileDialog.getOpenFileName(self, "Add Song", "", "CSEQ Files (*.cseq);;All Files (*)")
        if not path:
            return

        self._editor.add_song(self.hwl, Path(path).read_bytes())
        self._mark_modified()
        self._rebuild_tree()

    def _export_song(self, index: int):
        path, _ = QFileDialog.getSaveFileName(self, f"Export Song {index}", f"song_{index}.cseq", "CSEQ Files (*.cseq)")
        if path:
            Path(path).write_bytes(self.hwl.songs[index])
            self.status.showMessage(f"Exported song {index}")

    def _replace_song(self, index: int):
        path, _ = QFileDialog.getOpenFileName(self, f"Replace Song {index}", "", "CSEQ Files (*.cseq);;All Files (*)")
        if not path:
            return

        self._editor.replace_song(self.hwl, index, Path(path).read_bytes())
        self._mark_modified()
        self._rebuild_tree()

    def _remove_song(self, index: int):
        if QMessageBox.question(self, "Remove Song", f"Remove song {index}?") == QMessageBox.Yes:
            self._editor.remove_song(self.hwl, index)
            self._mark_modified()
            self._rebuild_tree()

    def _build_bank_from_vags(self):
        if not self.hwl:
            return

        files, _ = QFileDialog.getOpenFileNames(self, "Select VAG Files", "", "VAG Files (*.vag);;All Files (*)")
        if not files:
            return

        try:
            result = self._bank_builder.build_from_files(files, self.hwl.spu_addrs)
            self._editor.add_bank(self.hwl, result.bank_data)
            self._mark_modified()
            self._rebuild_tree()

            QMessageBox.information(self, "Bank Created",
                f"Bank {len(self.hwl.banks) - 1} created with {len(files)} samples.\n"
                f"SPU indices: {', '.join(map(str, result.new_spu_indices))}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed:\n{e}\n{traceback.format_exc()}")

    def _midi_to_cseq(self):
        if not self.hwl or not HAS_MIDO:
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select MIDI", "", "MIDI Files (*.mid *.midi)")
        if not path:
            return

        try:
            info = self._midi_converter.get_midi_info(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read MIDI:\n{e}")
            return

        dialog = MidiMappingDialog(self, info, len(self.hwl.spu_addrs))
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            cseq_data = self._midi_converter.convert(path, dialog.get_settings())
            self._editor.add_song(self.hwl, cseq_data)
            self._mark_modified()
            self._rebuild_tree()
            self.status.showMessage(f"Converted MIDI and added as song {len(self.hwl.songs) - 1}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Conversion failed:\n{e}")

    def closeEvent(self, event):
        if self._check_unsaved():
            event.accept()
        else:
            event.ignore()
