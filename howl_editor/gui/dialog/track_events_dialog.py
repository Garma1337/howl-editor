# coding: utf-8

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, )

from howl_editor.ctr.formats.cseq.models import (
    CSEQ_EVENT_PARAMS, CseqEventType, CseqSong,
)
from howl_editor.gui.layout import WindowSize


class TrackEventsDialog(QDialog):

    def __init__(
        self, parent, title: str, song: CseqSong,
        on_replace_track: Callable[[int], None] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(WindowSize.TRACK_EVENTS_WIDTH, WindowSize.TRACK_EVENTS_HEIGHT)
        self._song = song
        self._on_replace_track = on_replace_track
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
            flavor = "drum" if track.is_drum else "melodic"
            label = f"Track {i} · {flavor} · {len(track.events)} events"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, i)
            self._track_list.addItem(item)
        self._track_list.currentRowChanged.connect(self._show_track)
        splitter.addWidget(self._track_list)

        self._event_table = QTableWidget(0, 4)
        self._event_table.setHorizontalHeaderLabels(["Δ", "Event", "Param 1", "Param 2"])
        self._event_table.verticalHeader().setVisible(False)
        self._event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._event_table.setSelectionMode(QTableWidget.NoSelection)
        self._event_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents,
        )
        self._event_table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self._event_table)
        splitter.setSizes([220, 540])
        layout.addWidget(splitter, stretch=1)

        bottom_row = QHBoxLayout()

        if self._on_replace_track is not None:
            replace_btn = QPushButton("🎼  Replace selected track from MIDI…")
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
        if row < 0 or self._on_replace_track is None:
            return

        # Close before invoking the callback — the caller refreshes the
        # Workshop which will reopen this dialog if the user wants another
        # look. Keeping it open would show stale events anyway.
        self.accept()
        self._on_replace_track(row)

    def _show_track(self, row: int) -> None:
        self._event_table.setRowCount(0)

        if row < 0 or row >= len(self._song.tracks):
            return

        track = self._song.tracks[row]
        for event in track.events:
            event_row = self._event_table.rowCount()
            self._event_table.insertRow(event_row)

            self._event_table.setItem(
                event_row, 0, self._make_item(f"+{event.delta}"),
            )
            self._event_table.setItem(
                event_row, 1, self._make_item(self._event_type_name(event.event_type)),
            )

            param_1, param_2 = self._format_params(event)
            self._event_table.setItem(event_row, 2, self._make_item(param_1))
            self._event_table.setItem(event_row, 3, self._make_item(param_2))

    def _format_params(self, event) -> tuple[str, str]:
        # CSEQ events store up to two byte params. We label them by event
        # type so a reader can scan vertically — NOTE_ON shows
        # pitch+velocity, VELOCITY only shows the velocity column, etc.
        params = CSEQ_EVENT_PARAMS.get(event.event_type, 0)
        et = event.event_type

        if et == CseqEventType.NOTE_ON:
            return f"pitch={event.pitch}", f"vel={event.velocity}"

        if et == CseqEventType.NOTE_OFF:
            return f"pitch={event.pitch}", ""

        if et == CseqEventType.VELOCITY:
            return f"vel={event.velocity}", ""

        if et == CseqEventType.PAN:
            return f"pan={event.velocity}", ""

        if et == CseqEventType.CHANGE_PATCH:
            return f"patch={event.velocity}", ""

        if et == CseqEventType.PITCH_BEND:
            return f"bend={event.velocity}", ""

        if params == 0:
            return "", ""

        # Fallback for the UNKNOWN_* / END_TRACK_2 types so the table still
        # shows the raw bytes the reader saw.
        return f"p={event.pitch}", f"v={event.velocity}" if params > 1 else ""

    @staticmethod
    def _event_type_name(event_type: CseqEventType) -> str:
        try:
            return event_type.name
        except AttributeError:
            return f"0x{int(event_type):02X}"

    @staticmethod
    def _make_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item
