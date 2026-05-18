# coding: utf-8

"""BNK binary layout — numbers reader and writer must agree on.

File structure overview:

    +-------------------------------+
    | u16 sample count              |  SAMPLE_COUNT_SIZE
    +-------------------------------+
    | i16 sample id × N             |  N × SAMPLE_ID_SIZE
    +-------------------------------+
    | (zero pad to next sector)     |
    +-------------------------------+
    | sample 0 raw bytes            |
    | sample 1 …                    |
    +-------------------------------+
"""

# Width of the leading u16 sample-count field.
SAMPLE_COUNT_SIZE = 2

# Width of each i16 sample-ID entry in the header table.
SAMPLE_ID_SIZE = 2

# Upper sanity bound on the sample count — anything at or above this
# is treated as a corrupt / non-bank blob and the reader returns empty.
MAX_SAMPLE_COUNT = 1024
