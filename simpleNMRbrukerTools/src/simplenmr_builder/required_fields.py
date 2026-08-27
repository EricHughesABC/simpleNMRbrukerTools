"""
Per-source required-field checking.

Two distinct failure modes on purpose:
  - Missing a NO_FALLBACK field (smiles, molfile, carbonAtomsInfo) is a
    hard error the builder refuses to proceed past, because the server
    has no graceful fallback and will crash with an uncaught KeyError.
  - Missing any other required-for-this-source field is also an error
    (the builder shouldn't silently produce a submission that's missing
    something its own contract says that source must include), but is
    reported distinctly so callers can tell the two apart if they want to.
  - Including a field that's confirmed FORBIDDEN for a source (e.g.
    nmrAssignments/exptIdentifiers for jeol) is also an error — JEOL
    genuinely never emits these, and silently including them would be a
    real, novel divergence from every confirmed real JEOL submission.
"""

from __future__ import annotations

from .constants import NO_FALLBACK_FIELDS, REQUIRED_EVERYWHERE, SOURCE_FORBIDDEN, SOURCE_REQUIRED_EXTRA, SOURCES


class ContractError(ValueError):
    """Base class for contract-violation errors raised while building a payload."""


class MissingNoFallbackFieldError(ContractError):
    """A field with no server-side graceful fallback is missing. The server
    will crash with an uncaught KeyError rather than fail gracefully."""


class MissingRequiredFieldError(ContractError):
    """A field required for this source is missing."""


class ForbiddenFieldPresentError(ContractError):
    """A field confirmed absent for this source was included anyway."""


def required_fields_for(source: str) -> frozenset[str]:
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}, expected one of {SOURCES}")
    return REQUIRED_EVERYWHERE | SOURCE_REQUIRED_EXTRA.get(source, frozenset())


def forbidden_fields_for(source: str) -> frozenset[str]:
    return SOURCE_FORBIDDEN.get(source, frozenset())


def validate_required(payload: dict, source: str) -> None:
    """Raise on missing required fields, forbidden fields present, or any
    missing NO_FALLBACK field (raised first/separately since it's the most
    dangerous failure mode)."""
    present = set(payload.keys())

    missing_no_fallback = sorted(NO_FALLBACK_FIELDS - present)
    if missing_no_fallback:
        raise MissingNoFallbackFieldError(
            f"missing field(s) with no server-side fallback (server will crash): {missing_no_fallback}"
        )

    missing_required = sorted(required_fields_for(source) - present)
    if missing_required:
        raise MissingRequiredFieldError(f"missing field(s) required for source={source!r}: {missing_required}")

    forbidden_present = sorted(forbidden_fields_for(source) & present)
    if forbidden_present:
        raise ForbiddenFieldPresentError(
            f"field(s) confirmed absent for source={source!r} were included: {forbidden_present}"
        )
