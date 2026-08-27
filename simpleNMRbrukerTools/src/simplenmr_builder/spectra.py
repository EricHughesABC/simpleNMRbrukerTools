"""
Spectrum-block construction: multi-block numbering, chosenSpectra, and
exptIdentifiers.

Three things this module gets right on purpose, because getting them
wrong is exactly how bugs like the JEOL SKIP leak happen:

1. Multi-block is a first-class, supported case for ALL 10 NMREXPERIMENTS
   types (confirmed by Eric directly), not just HMBC/HSQC. Callers add as
   many blocks per token as they like; this module numbers them `_0`,
   `_1`, ... automatically.

2. chosenSpectra and exptIdentifiers are NOT the same list with different
   names. chosenSpectra is the user's filtered "what to actually use"
   list (SKIP'd entries removed before submission, for Bruker/JEOL).
   exptIdentifiers is Bruker's full raw-experiment list, where "SKIP"
   means "the auto-classifier couldn't recognize this," a different
   concept that happens to share the same string. JEOL never submits
   exptIdentifiers at all. Mixing these two up would silently produce a
   payload that looks right but misrepresents what the user chose.

3. SKIP-filtering for chosenSpectra always goes through skip.filter_skip
   (a fresh list comprehension), never a hand-rolled mutate-while-
   iterating loop.
"""

from __future__ import annotations

from typing import Any

from .constants import HSQC, NMREXPERIMENTS
from .envelope import spectrum_block_envelope, string_list_envelope
from .skip import filter_skip, is_skip_string


class SpectrumBuilder:
    def __init__(self) -> None:
        self._blocks: dict[str, list[dict]] = {}
        self._chosen_candidates: list[tuple[str, bool]] = []  # (entry_string, is_skip)
        self._expt_identifier_candidates: list[str] = []
        self._spectra_with_peaks_candidates: list[str] = []

    # -- spectrum blocks -------------------------------------------------

    def add_block(self, token: str, block: dict) -> None:
        """Add one spectrum block for a NMREXPERIMENTS token. Safe to call
        more than once per token — multi-block is expected, not special."""
        if token not in NMREXPERIMENTS:
            raise ValueError(f"{token!r} is not a recognized NMREXPERIMENTS token: {NMREXPERIMENTS}")
        self._blocks.setdefault(token, []).append(spectrum_block_envelope(block))

    def has_hsqc(self) -> bool:
        return bool(self._blocks.get(HSQC))

    def build_blocks(self) -> dict[str, dict]:
        """Return {"<TOKEN>_<N>": block, ...} for every added block."""
        out: dict[str, dict] = {}
        for token, blocks in self._blocks.items():
            for i, block in enumerate(blocks):
                out[f"{token}_{i}"] = block
        return out

    # -- chosenSpectra -----------------------------------------------------

    def add_chosen_candidate(self, entry: str, skip: bool = False) -> None:
        """
        Register one spectrum's chosenSpectra entry string
        ("<...metadata...> <exptype>"), plus whether the user marked it
        SKIP. The final chosenSpectra list is built by filtering these at
        build() time — never by mutating a list as entries are added.
        """
        self._chosen_candidates.append((entry, skip))

    def build_chosen_spectra(self) -> dict:
        """
        Build the chosenSpectra envelope. Bruker/JEOL both intend to
        filter SKIP'd spectra out client-side before submission (unlike
        MNova, which includes the literal SKIP token and lets the server
        strip it) — this filters using the explicit `skip` flag recorded
        by add_chosen_candidate, via skip.filter_skip. Values are plain
        strings (confirmed against real submitted files and the live
        Bruker converter), not wrapped in a sub-dict.
        """
        kept = filter_skip(self._chosen_candidates, is_skip=lambda pair: pair[1])
        entries = [entry for entry, _skip in kept]
        return string_list_envelope(entries, datatype="chosenSpectra")

    # -- exptIdentifiers (bruker only) --------------------------------------

    def add_expt_identifier(self, entry: str) -> None:
        """
        Register one raw-experiment entry for exptIdentifiers. Unlike
        chosenSpectra, this is NOT filtered — it's meant to carry every
        raw experiment TopSpin detected, including ones the classifier
        tagged "SKIP" because it couldn't recognize the type. Only call
        this for a Bruker build; JEOL must omit exptIdentifiers entirely.
        """
        self._expt_identifier_candidates.append(entry)

    def build_expt_identifiers(self) -> dict:
        return string_list_envelope(self._expt_identifier_candidates, datatype="exptIdentifiers")

    # -- spectraWithPeaks --------------------------------------------------

    def add_spectrum_with_peaks(self, entry: str) -> None:
        """
        Register one entry for spectraWithPeaks. Shape confirmed against a
        real Bruker submission: a string-list envelope like chosenSpectra/
        exptIdentifiers, one entry per spectrum that has actual peak data
        (real example: "[1H, 13C] HSQC hsqcedetgpsp.3 3.ser_0"). Manifest
        marks requiredness as still unknown, so builder callers may omit
        this entirely; if omitted, build_spectra_with_peaks() below is
        simply not called by SimpleNMRBuilder.
        """
        self._spectra_with_peaks_candidates.append(entry)

    def build_spectra_with_peaks(self) -> dict:
        return string_list_envelope(self._spectra_with_peaks_candidates, datatype="spectraWithPeaks")

    def has_spectra_with_peaks(self) -> bool:
        return bool(self._spectra_with_peaks_candidates)
