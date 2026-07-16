# coding: utf-8

"""CTR engine-wide audio limits."""

# A song sequence is read into a fixed 0x5800-byte buffer with no bounds check,
# so an oversized song overruns adjacent memory.
MAX_CSEQ_BYTES = 0x5800

# The engine keeps at most 8 banks resident in SPU RAM at once.
MAX_RESIDENT_BANKS = 8

# The engine uploads samples starting at SPU byte 0x1010 and skips any
# sample whose end address would reach 0x7E000 — the top 0x2000 of SPU RAM
# is left for the reverb work area. A sample that would cross the ceiling
# is silently not uploaded.
SPU_SAMPLE_CEILING = 0x7E000                                    # end address must stay below this
SPU_HEAP_START = 0x1010                                         # first byte samples upload to
SPU_USABLE_SAMPLE_BYTES = SPU_SAMPLE_CEILING - SPU_HEAP_START   # 0x7CFF0 = 511984 bytes
