# coding: utf-8

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, )

from howl_editor.ctr.formats.cseq.models import (
    CSEQ_EDITABLE_EVENTS, CSEQ_EVENT_PARAMS, CseqEventType, CseqSong,
)
from howl_editor.gui.dialog.edit_event_dialog import EditEventDialog
from howl_editor.gui.handler.sequence_event_editor import SequenceEventEditor
from howl_editor.gui.layout import WindowSize


class TrackEventsDialog(QDialog):

    def __init__(
        self, parent, title: str, song: CseqSong,
        editor: SequenceEventEditor | None = None,
        instrument_count: int = 0,
        percussion_count: int = 0,
    ):
        """`editor` is a SequenceEventEditor already bound to the song and
        sequence being shown; passing None makes the dialog read-only."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(WindowSize.TRACK_EVENTS_WIDTH, WindowSize.TRACK_EVENTS_HEIGHT)
        self._song = song
        self._instrument_count = instrument_count
        self._percussion_count = percussion_count
        self._editor = editor
        self._build_ui()

        if song.tracks:
            self._track_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<b>{self._song.bpm}</b> BPM · "
            f"<b>{self._song.tpqn}</b> ticks per quarter · "
            f"<b>{len(self._song.tracks)}</b> tracks",
        )
        layout.addWidget(summary)

        splitter = QSplitter(Qt.Horizontal)

        self._track_list = QListWidget()
        for i, track in enumerate(self._song.tracks):
            item = QListWidgetItem(self._track_label(i))
            item.setData(Qt.UserRole, i)
            self._track_list.addItem(item)
        self._track_list.currentRowChanged.connect(self._show_track)
        splitter.addWidget(self._track_list)

        self._event_table = QTableWidget(0, 4)
        self._event_table.setHorizontalHeaderLabels(["Δ", "Event", "Param 1", "Param 2"])
        self._event_table.verticalHeader().setVisible(False)
        self._event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._event_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._event_table.setSelectionMode(
            QTableWidget.SingleSelection if self._editing_enabled()
            else QTableWidget.NoSelection,
        )
        self._event_table.itemSelectionChanged.connect(self._refresh_event_buttons)
        self._event_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents,
        )
        self._event_table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self._event_table)
        splitter.setSizes([220, 540])
        layout.addWidget(splitter, stretch=1)

        if self._editing_enabled():
            layout.addLayout(self._build_event_buttons())

        bottom_row = QHBoxLayout()

        if self._editor is not None:
            replace_btn = QPushButton("🎼  Replace from MIDI…")
            replace_btn.setToolTip(
                "Pick a MIDI file and overwrite the currently-selected "
                "track's events. Track flags / instrument stay put.",
            )
            replace_btn.clicked.connect(self._fire_replace)
            bottom_row.addWidget(replace_btn)

        bottom_row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        bottom_row.addWidget(buttons)
        layout.addLayout(bottom_row)

    def _fire_replace(self) -> None:
        row = self._track_list.currentRow()
        if row < 0 or self._editor is None:
            return

        # Close before invoking the callback — the caller refreshes the
        # Workshop which will reopen this dialog if the user wants another
        # look. Keeping it open would show stale events anyway.
        self.accept()
        self._editor.replace_track_from_midi(row)

    def _track_label(self, index: int) -> str:
        track = self._song.tracks[index]
        flavor = "drum" if track.is_drum else "melodic"
        return f"Track {index} · {flavor} · {len(track.events)} events"

    def _refresh_track_label(self, index: int) -> None:
        item = self._track_list.item(index)

        if item is not None and 0 <= index < len(self._song.tracks):
            item.setText(self._track_label(index))

    def _editing_enabled(self) -> bool:
        return self._editor is not None

    def _build_event_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()

        hint = QLabel(
            "Modulation events (volume / pan / reverb / pitch bend) re-apply "
            "to notes already sounding:",
        )
        hint.setWordWrap(True)
        row.addWidget(hint)
        row.addStretch(1)

        self._edit_event_btn = QPushButton("✏️  Edit value…")
        self._edit_event_btn.clicked.connect(self._do_edit_event)
        row.addWidget(self._edit_event_btn)

        self._insert_event_btn = QPushButton("➕  Insert before…")
        self._insert_event_btn.setToolTip(
            "Insert a modulation event before the selected one. CTR has no "
            "ramp primitive — a smooth bend or fade is a dense run of these.",
        )
        self._insert_event_btn.clicked.connect(self._do_insert_event)
        row.addWidget(self._insert_event_btn)

        self._delete_event_btn = QPushButton("🗑️  Delete")
        self._delete_event_btn.setToolTip(
            "Remove the selected modulation event. Its delta is folded into "
            "the next event so nothing later in the track shifts earlier.",
        )
        self._delete_event_btn.clicked.connect(self._do_delete_event)
        row.addWidget(self._delete_event_btn)

        self._refresh_event_buttons()
        return row

    def _refresh_event_buttons(self) -> None:
        if not self._editing_enabled():
            return

        event = self._selected_event()
        editable = event is not None and event.event_type in CSEQ_EDITABLE_EVENTS

        self._edit_event_btn.setEnabled(editable)
        self._delete_event_btn.setEnabled(editable)
        self._insert_event_btn.setEnabled(event is not None)

    def _selected_event_index(self) -> int:
        rows = self._event_table.selectionModel().selectedRows() if self._event_table.selectionModel() else []
        return rows[0].row() if rows else -1

    def _current_track_index(self) -> int:
        return self._track_list.currentRow()

    def _selected_event(self):
        track_idx = self._current_track_index()
        event_idx = self._selected_event_index()

        if track_idx < 0 or track_idx >= len(self._song.tracks) or event_idx < 0:
            return None

        events = self._song.tracks[track_idx].events
        return events[event_idx] if event_idx < len(events) else None

    def _do_edit_event(self) -> None:
        event = self._selected_event()

        if event is None or self._editor is None:
            return

        dialog = EditEventDialog(
            self, event.event_type, event.pitch, event.velocity, event.delta,
            is_drum=self._current_track_is_drum(),
            descriptor_count=self._descriptor_count_for_current_track(),
        )

        if dialog.exec() != QDialog.Accepted:
            return

        result = dialog.chosen()
        self._apply(self._editor.edit_event(
            self._current_track_index(), self._selected_event_index(),
            result.pitch, result.velocity, result.delta,
        ))

    def _do_insert_event(self) -> None:
        event = self._selected_event()

        if event is None or self._editor is None:
            return

        seed = event.pitch if event.event_type in CSEQ_EDITABLE_EVENTS else 0
        dialog = EditEventDialog(
            self, None, seed,
            is_drum=self._current_track_is_drum(),
            descriptor_count=self._descriptor_count_for_current_track(),
        )

        if dialog.exec() != QDialog.Accepted:
            return

        result = dialog.chosen()
        self._apply(self._editor.insert_event(
            self._current_track_index(), self._selected_event_index(),
            result.event_type, result.pitch, result.velocity, result.delta,
        ))

    def _current_track_is_drum(self) -> bool:
        idx = self._current_track_index()
        return 0 <= idx < len(self._song.tracks) and self._song.tracks[idx].is_drum

    def _descriptor_count_for_current_track(self) -> int:
        """How many descriptors the current track can address, so the edit
        dialog can tell the user the legal index range. Drum tracks index the
        percussion table, melodic tracks the instrument table."""
        return (
            self._percussion_count if self._current_track_is_drum()
            else self._instrument_count
        )

    def _do_delete_event(self) -> None:
        if self._selected_event() is None or self._editor is None:
            return

        self._apply(self._editor.delete_event(
            self._current_track_index(), self._selected_event_index(),
        ))

    def _apply(self, new_song: CseqSong | None) -> None:
        """Adopt the re-read song a mutation callback handed back, keeping the
        user on the same track and row so a run of edits doesn't lose place."""
        if new_song is None:
            return

        track_idx = self._current_track_index()
        event_idx = self._selected_event_index()
        self._song = new_song
        self._show_track(track_idx)
        self._refresh_track_label(track_idx)

        events = self._song.tracks[track_idx].events if 0 <= track_idx < len(self._song.tracks) else []

        if events:
            self._event_table.selectRow(min(event_idx, len(events) - 1))

        self._refresh_event_buttons()

    def _show_track(self, row: int) -> None:
        self._event_table.setRowCount(0)

        if row < 0 or row >= len(self._song.tracks):
            return

        track = self._song.tracks[row]
        for event in track.events:
            event_row = self._event_table.rowCount()
            self._event_table.insertRow(event_row)

            self._event_table.setItem(
                event_row, 0, self.make_item(f"+{event.delta}"),
            )
            self._event_table.setItem(
                event_row, 1, self.make_item(self.event_type_name(event.event_type)),
            )

            param_1, param_2 = self._format_params(event)
            self._event_table.setItem(event_row, 2, self.make_item(param_1))
            self._event_table.setItem(event_row, 3, self.make_item(param_2))

    def _format_params(self, event) -> tuple[str, str]:
        # CSEQ events store up to two byte params. We label them by event
        # type so a reader can scan vertically — NOTE_ON shows
        # pitch+velocity, VELOCITY only shows the volume column, etc.
        #
        # Every single-param event keeps its byte in `pitch`; the reader only
        # fills `velocity` for the two-param NOTE_ON. Reading `velocity` here
        # is what used to render all four modulation events as a flat 0.
        params = CSEQ_EVENT_PARAMS.get(event.event_type, 0)
        et = event.event_type

        if et == CseqEventType.NOTE_ON:
            return f"pitch={event.pitch}", f"vel={event.velocity}"

        if et == CseqEventType.NOTE_OFF:
            return f"pitch={event.pitch}", ""

        if et == CseqEventType.VELOCITY:
            return f"vol={event.pitch}", EditEventDialog.describe(et, event.pitch)

        if et == CseqEventType.PAN:
            return f"pan={event.pitch}", EditEventDialog.describe(et, event.pitch)

        if et == CseqEventType.REVERB:
            return f"reverb={event.pitch}", EditEventDialog.describe(et, event.pitch)

        if et == CseqEventType.CHANGE_PATCH:
            return f"patch={event.pitch}", ""

        if et == CseqEventType.PITCH_BEND:
            return f"bend={event.pitch}", EditEventDialog.describe(et, event.pitch)

        if params == 0:
            return "", ""

        # Fallback for UNKNOWN_4 / END_TRACK_2 so the table still shows the
        # raw bytes the reader saw.
        return f"p={event.pitch}", f"v={event.velocity}" if params > 1 else ""

    @staticmethod
    def event_type_name(event_type: CseqEventType) -> str:
        try:
            return event_type.name
        except AttributeError:
            return f"0x{int(event_type):02X}"

    @staticmethod
    def make_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item
