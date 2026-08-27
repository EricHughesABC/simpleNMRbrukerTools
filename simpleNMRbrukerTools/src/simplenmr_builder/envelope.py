"""
Envelope construction for the three JSON shapes confirmed in the manifest.

Every field envelope is {"datatype": str, "count": int, "data": {...}}.
There are essentially no real JSON arrays anywhere in real submitted
files — everything list-like is a dict keyed by *stringified* index
("0", "1", "2", ...). This module is the single place that builds that
shape, so nothing downstream has to remember the convention.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _datatype_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "string"


def scalar_envelope(value: Any, datatype: str | None = None) -> dict:
    """
    Singleton scalar field, parsed server-side via DataFrame(data, index=[0]).

    data = {"0": value}
    """
    return {
        "datatype": datatype or _datatype_name(value),
        "count": 1,
        "data": {"0": value},
    }


def indexed_envelope(records: Sequence[Mapping[str, Any]], datatype: str = "dataframe") -> dict:
    """
    Indexed/dict field (allAtomsInfo, carbonAtomsInfo, nmrAssignments,
    c13predictions, ...), parsed server-side via
    DataFrame.from_dict(data, orient="index").

    data = {"0": {...record...}, "1": {...record...}, ...}

    `records` must be an actual Python list — never mutate the list you
    pass in while iterating over it; build a fresh filtered list first if
    filtering is needed (see skip.filter_skip).
    """
    return {
        "datatype": datatype,
        "count": len(records),
        "data": {str(i): dict(rec) for i, rec in enumerate(records)},
    }


def string_list_envelope(strings: Sequence[str], datatype: str = "special") -> dict:
    """
    The "special" shape used by chosenSpectra / exptIdentifiers /
    spectraWithPeaks: a dict of PLAIN STRING values keyed by stringified
    index — NOT a dict of records. Confirmed directly against real
    submitted files and the live Bruker converter
    (core/json_converter.py: {str(i): spec for i, spec in enumerate(...)}).

    data = {"0": "13C 1D zgpg30 file.fid_2 HSQC", "1": "...", ...}
    """
    return {
        "datatype": datatype,
        "count": len(strings),
        "data": {str(i): s for i, s in enumerate(strings)},
    }


def spectrum_block_envelope(block: Mapping[str, Any]) -> dict:
    """
    A single spectrum block's own envelope. The block must set its own
    "type" field to "1D" or "2D" — that field, not the eventual top-level
    key name, is what the server uses to parse it.
    """
    if "type" not in block:
        raise ValueError('spectrum block is missing required "type" field ("1D" or "2D")')
    return dict(block)
