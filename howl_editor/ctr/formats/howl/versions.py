# coding: utf-8

"""Known values of the HOWL file's version byte (offset 4 of the header)."""

KNOWN_VERSIONS: dict[int, str] = {
    0x6F: "Demo (Test Drive)",
    0x71: "Demo (OPSM)",
    0x72: "Demo (Spyro)",
    0x78: "Beta (Aug 5)",
    0x7D: "Prototype",
    0x80: "Release",
}
