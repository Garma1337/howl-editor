# coding: utf-8


class IconSize:
    """Icon dimensions in pixels."""

    LEAF = 22            # leaf-row icons (samples, sequences) + hub-combo dropdown
    ENTRY = 32           # entry-row icons (tracks, banks, FX)
    CATEGORY_TITLE = 40  # category detail-view title icon
    CARD = 64            # category-card grid icons


class ButtonWidth:
    """Fixed pixel widths for buttons that need a stable footprint."""

    # Leaf-row action buttons.
    LEAF_PLAY = 64
    LEAF_REPLACE = 82
    LEAF_EXPORT = 78

    # Entry-row action buttons.
    ENTRY_TOGGLE = 26
    ENTRY_RESET = 74
    ENTRY_EXPORT = 118
    HUB_PLAY = 122
    HUB_REPLACE = 126

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

    MERGE_BANK_WIDTH = 750
    MERGE_BANK_HEIGHT = 550

    CONVERT_MIDI_WIDTH = 720
    CONVERT_MIDI_HEIGHT = 520


class Inset:
    """Reusable inset / padding values."""

    BODY = 8  # default inset for entry-row body content
