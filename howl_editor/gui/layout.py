# coding: utf-8


class IconSize:
    """Icon dimensions in pixels."""

    LEAF = 22            # leaf-row icons (samples, sequences) + hub-combo dropdown
    ENTRY = 32           # entry-row icons (tracks, banks, FX)
    CATEGORY_TITLE = 40  # category detail-view title icon
    CARD = 64            # category-card grid icons


class ButtonWidth:
    """Fixed pixel widths for buttons that need a stable footprint."""

    # Leaf-row action buttons (icon-only).
    LEAF_PLAY = 32
    LEAF_ACTIONS = 52    # extra width covers Qt's menu indicator arrow

    # Entry-row action buttons (icon-only).
    ENTRY_TOGGLE = 26
    ENTRY_ACTIONS = 56   # extra width covers Qt's menu indicator arrow
    HUB_PLAY = 122

    # Category navigation.
    BACK = 130

    # Player widget.
    PLAYER_BUTTON = 32
    PLAYER_TIME = 90
    PLAYER_LABEL_MIN = 100


class WindowSize:
    """Default startup sizes for the main window and standalone dialogs."""

    MAIN_WIDTH = 1300
    MAIN_HEIGHT = 900

    SAPHI_EXPORT_WIDTH = 420
    SAPHI_EXPORT_HEIGHT = 220

    EXPORT_WIDTH = 250
    EXPORT_HEIGHT = 125

    COPY_SAMPLE_WIDTH = 420
    COPY_SAMPLE_HEIGHT = 125

    EDIT_INSTRUMENT_WIDTH = 360
    EDIT_INSTRUMENT_HEIGHT = 150
    EDIT_INSTRUMENT_HEIGHT_WITH_ADSR = 200

    SELECT_SAMPLE_WIDTH = 480
    SELECT_SAMPLE_HEIGHT = 480

    TRACK_EVENTS_WIDTH = 760
    TRACK_EVENTS_HEIGHT = 560

    MIDI_EXPORT_WIDTH = 380
    MIDI_EXPORT_HEIGHT = 150

    MERGE_BANK_WIDTH = 750
    MERGE_BANK_HEIGHT = 550

    CONVERT_MIDI_WIDTH = 720
    CONVERT_MIDI_HEIGHT = 520


class Inset:
    """Reusable inset / padding values."""

    BODY = 8  # default inset for entry-row body content
