# coding: utf-8

from enum import Enum


class MidoMessageType(str, Enum):
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "control_change"
    PITCHWHEEL = "pitchwheel"
    PROGRAM_CHANGE = "program_change"

    SET_TEMPO = "set_tempo"
    END_OF_TRACK = "end_of_track"
