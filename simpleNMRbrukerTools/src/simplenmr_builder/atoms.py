"""
Atom-info handling.

`atomNumber` is a free-form, user-facing DISPLAY LABEL (confirmed by Eric
directly) — NOT the molfile/RDKit structural index (that's the separate
`atom_idx` field). Users can set it to arbitrary strings, including primed
forms like "4'" or "5''". The server tolerates both int/float and string
input (numeric-looking strings get coerced to int server-side, non-numeric
ones are kept as-is) — but that tolerance is a display convenience, not
evidence the field is "really" numeric. This module treats it as a label
throughout: always stored/emitted as a string, whatever the caller passes
in, so a caller can't accidentally lose a primed label to numeric coercion
upstream of the server.
"""

from __future__ import annotations

from typing import Any, Mapping

from .constants import CARBON_ATOMS_INFO_REQUIRED_COLUMNS, NMR_ASSIGNMENTS_REQUIRED_COLUMNS
from .envelope import indexed_envelope


def normalize_atom_number(value: Any) -> str:
    """Always return atomNumber as a string label, e.g. 42 -> "42", "4'" -> "4'"."""
    return str(value)


def build_atom_record(atom_idx: int, atom_number: Any, **extra: Any) -> dict:
    """
    Build one atom-info record with atomNumber normalized to a string
    label. `extra` is passed through as-is (e.g. element, ppm, etc.).
    """
    record = {"atom_idx": int(atom_idx), "atomNumber": normalize_atom_number(atom_number)}
    record.update(extra)
    return record


def _check_required_columns(records: list[Mapping[str, Any]], required: tuple[str, ...], field_name: str) -> None:
    for i, rec in enumerate(records):
        missing = [c for c in required if c not in rec]
        if missing:
            raise ValueError(f"{field_name} record at index {i} is missing required column(s): {missing}")


def build_carbon_atoms_info(records: list[dict]) -> dict:
    """
    Build the carbonAtomsInfo envelope. Server minimally needs atom_idx and
    atomNumber on each record — other columns submitted here (ppm,
    ppm_calculated, iupacLabel, jCouplingVals, jCouplingClass, H1_ppm,
    visible, x, y) are overwritten server-side anyway, so they're not
    required, but are passed through if present.
    """
    _check_required_columns(records, CARBON_ATOMS_INFO_REQUIRED_COLUMNS, "carbonAtomsInfo")
    return indexed_envelope(records)


def build_all_atoms_info(records: list[dict]) -> dict:
    """allAtomsInfo has no separately-confirmed minimal column set beyond
    being a well-formed indexed_dict; callers should still include
    atom_idx/atomNumber for consistency with carbonAtomsInfo."""
    return indexed_envelope(records)


def build_nmr_assignments(records: list[dict]) -> dict:
    """
    Build nmrAssignments (required for bruker, must be OMITTED for jeol —
    see constants.SOURCE_FORBIDDEN). Required columns: f1_ppm, atom_idx,
    atomNumber, f2_ppm1, f2_ppm2. x/y/jCouplingVals/jCouplingClass/
    sym_atom_idx/sym_atomNumber are added or overwritten server-side.
    """
    _check_required_columns(records, NMR_ASSIGNMENTS_REQUIRED_COLUMNS, "nmrAssignments")
    return indexed_envelope(records)
