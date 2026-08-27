"""
Constants and per-source requirement tables for the simpleNMR JSON contract.

Source of truth: simpleNMR_field_manifest.yaml (fourth pass, 2026-08-26).
Do not hand-edit these tables without re-checking the manifest — they encode
facts confirmed by direct code reading and Eric's own statements, not
guesses.
"""

from __future__ import annotations

# The 10 literal NMREXPERIMENTS tokens (config/globals.py, confirmed by
# direct read). All 10 classify/parse into dataframes; NOESY is the one
# token never consumed by any server-side solving logic (inert passthrough).
NMREXPERIMENTS = (
    "H1_1D",
    "C13_1D",
    "DEPT135",
    "HSQC",
    "HMBC",
    "COSY",
    "NOESY",
    "H1_pureshift",
    "HSQC_CLIPCOSY",
    "DDEPTCH3ONLY",
)

# The only unconditionally hard-required spectrum type. Confirmed by code
# (core/nmrsolution.py, two independent checks) and directly by Eric.
HSQC = "HSQC"

# Spectrum types never consumed downstream despite classifying/parsing fine.
INERT_SPECTRUM_TYPES = frozenset({"NOESY"})

# Fields required on every submission, regardless of source (mnova, bruker,
# jason). This is the base set — see SOURCE_REQUIRED_EXTRA below for fields
# that are required for some sources only.
REQUIRED_EVERYWHERE = frozenset({
    "smiles",
    "molfile",
    "hostname",
    "allAtomsInfo",
    "carbonAtomsInfo",
    "MNOVAcalcMethod",
    "simulatedAnnealing",
    "ml_consent",
    "chosenSpectra",
})

# Fields with NO server-side graceful fallback: NMRProblem.add_missing_
# spectra's backfill safety net doesn't cover them, and they're read via
# unguarded dict indexing downstream. Missing one crashes the server with
# an uncaught KeyError. The builder refuses to construct a payload missing
# any of these, rather than silently passing through whatever it's given.
NO_FALLBACK_FIELDS = frozenset({"smiles", "molfile", "carbonAtomsInfo"})

# Recognized non-MNova sources this library builds for.
SOURCES = ("bruker", "jeol")

# Fields required for some sources but not others, on top of
# REQUIRED_EVERYWHERE. Keyed by source name.
SOURCE_REQUIRED_EXTRA = {
    "bruker": frozenset({"nmrAssignments", "exptIdentifiers", "carbonCalcPositionsMethod"}),
    "jeol": frozenset({"carbonCalcPositionsMethod"}),
}

# Fields that must NOT be included for a given source (confirmed absent by
# direct code read, not just sample-file diffing).
SOURCE_FORBIDDEN = {
    "bruker": frozenset(),
    "jeol": frozenset({"nmrAssignments", "exptIdentifiers"}),
}

# ---------------------------------------------------------------------------
# IMPORTANT, confirmed 2026-08-27 against github.com/EricHughesABC/
# simpleNMRjeolTools3 (branch: master): the manifest's claim that the
# JEOL SKIP-removal bug was fixed and the repo consolidated down to a
# single v8 file is NOT reflected in the actual repo state. The top-level
# simpleNMRjeolTools.py and simpleNMRjeolTools_v5.py STILL contain the
# original buggy mutate-while-iterating loop:
#
#     for assignment in self.spectra_assignments:
#         if assignment["experiment_type"] == "SKIP":
#             self.spectra_assignments.remove(assignment)
#
# Only development/simpleNMRjeolTools_v8.py has the list-comprehension
# fix. Per the manifest itself, JEOL's real deployed entry point is
# whatever path is configured in JASON's External Tools plugin, which is
# invisible from the repo structure — so it is genuinely possible the
# buggy top-level file is still what runs in production today, despite
# the manifest recording this as resolved/closed. This library's own
# skip.py is unaffected (it never had the bug), but Eric should confirm
# which file JASON is actually pointed at before treating this as closed.
# ---------------------------------------------------------------------------

# Simulated-annealing tuning cluster — deprecated from the contract. Only
# the boolean `simulatedAnnealing` matters going forward; these six were
# pulled from the user-facing dialog because typical users couldn't set
# them usefully. The builder never emits these; if a caller supplies them
# they are silently dropped (not an error — some old clients still pass
# them through).
DEPRECATED_SA_FIELDS = frozenset({
    "randomizeStart",
    "startingTemperature",
    "endingTemperature",
    "coolingRate",
    "numberOfSteps",
    "ppmGroupSeparation",
})

# The literal SKIP sentinel used inside chosenSpectra strings.
SKIP_TOKEN = "SKIP"

# Minimal columns the server actually reads as trusted input for
# carbonAtomsInfo — anything else in a record is either ignored or
# overwritten server-side (ppm, ppm_calculated, iupacLabel, jCouplingVals,
# jCouplingClass, H1_ppm, visible, x, y are all recomputed).
CARBON_ATOMS_INFO_REQUIRED_COLUMNS = ("atom_idx", "atomNumber")

# Minimal columns the server reads as trusted input for nmrAssignments
# records (f2_ppm3 is present in real files but explicitly unused).
NMR_ASSIGNMENTS_REQUIRED_COLUMNS = ("f1_ppm", "atom_idx", "atomNumber", "f2_ppm1", "f2_ppm2")
