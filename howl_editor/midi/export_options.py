# coding: utf-8

from dataclasses import dataclass


@dataclass(frozen=True)
class MidiExportOptions:
    """Toggles that adjust what the MIDI exporter writes.

    `include_volume_events` — emit mid-song VELOCITY changes as CC #7 volume
    changes so the DAW reproduces CTR's volume curves.

    `apply_instrument_volume` — give each track a CC #7 volume at tick 0 from
    the volume field of the instrument it's bound to.

    Kept out of the exporter module so naming an option does not import mido.
    """
    include_volume_events: bool = True
    apply_instrument_volume: bool = False
