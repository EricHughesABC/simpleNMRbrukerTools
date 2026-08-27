"""
SimpleNMRBuilder — the public API Bruker and JEOL converters should import
instead of each hand-rolling their own JSON construction.

    builder = SimpleNMRBuilder(source="bruker")
    builder.set_scalar("smiles", "...")
    builder.set_scalar("molfile", "...")
    builder.set_scalar("hostname", "...")
    builder.set_scalar("MNOVAcalcMethod", "NMRSHIFTDB2 Predict")
    builder.set_scalar("simulatedAnnealing", True)
    builder.set_scalar("ml_consent", False)
    builder.set_scalar("carbonCalcPositionsMethod", "...")
    builder.set_all_atoms_info([...])
    builder.set_carbon_atoms_info([...])
    builder.set_nmr_assignments([...])          # bruker only
    builder.spectra.add_block("HSQC", {...})
    builder.spectra.add_chosen_candidate("...", skip=False)
    builder.spectra.add_expt_identifier("...")  # bruker only
    payload = builder.build()

`build()` refuses to return a payload that's missing a NO_FALLBACK field,
missing a field required for this source, or includes a field confirmed
forbidden for this source. It also strips the deprecated SA tuning
cluster if a caller supplies it, and validates via
validate_simplenmr_json.py when available.
"""

from __future__ import annotations

from typing import Any

from .atoms import build_all_atoms_info, build_carbon_atoms_info, build_nmr_assignments
from .constants import DEPRECATED_SA_FIELDS, HSQC, SOURCES
from .envelope import scalar_envelope
from .required_fields import ContractError, validate_required
from .spectra import SpectrumBuilder
from .validation import validate_payload


class HSQCMissingError(ContractError):
    """No HSQC block was added. HSQC is the only unconditionally
    hard-required spectrum — every other spectrum type is genuinely
    optional at the contract level."""


class SimpleNMRBuilder:
    def __init__(self, source: str) -> None:
        if source not in SOURCES:
            raise ValueError(f"unknown source {source!r}, expected one of {SOURCES}")
        self.source = source
        self.spectra = SpectrumBuilder()
        self._scalars: dict[str, Any] = {}
        self._all_atoms_info: dict | None = None
        self._carbon_atoms_info: dict | None = None
        self._nmr_assignments: dict | None = None
        self._c13predictions: dict | None = None

    # -- scalars -----------------------------------------------------------

    def set_scalar(self, name: str, value: Any) -> None:
        """Set any singleton_scalar field (smiles, molfile, hostname,
        MNOVAcalcMethod, simulatedAnnealing, ml_consent,
        carbonCalcPositionsMethod, ...). Deprecated SA-cluster fields are
        silently ignored here — see DEPRECATED_SA_FIELDS."""
        if name in DEPRECATED_SA_FIELDS:
            return
        self._scalars[name] = value

    # -- atom info -----------------------------------------------------------

    def set_all_atoms_info(self, records: list[dict]) -> None:
        self._all_atoms_info = build_all_atoms_info(records)

    def set_carbon_atoms_info(self, records: list[dict]) -> None:
        self._carbon_atoms_info = build_carbon_atoms_info(records)

    def set_nmr_assignments(self, records: list[dict]) -> None:
        """Only call for bruker — jeol must never include nmrAssignments."""
        self._nmr_assignments = build_nmr_assignments(records)

    def set_c13predictions(self, records: list[dict]) -> None:
        """Legitimately empty/omitted when this source has no shift
        predictor available (Bruker/TopSpin has none)."""
        from .envelope import indexed_envelope

        self._c13predictions = indexed_envelope(records, datatype="c13predictions")

    # -- build ---------------------------------------------------------------

    def build(self, validator_path: str | None = None, run_validation: bool = True) -> dict:
        if not self.spectra.has_hsqc():
            raise HSQCMissingError("no HSQC block was added; HSQC is the only hard-required spectrum type")

        payload: dict[str, Any] = {}

        for name, value in self._scalars.items():
            payload[name] = scalar_envelope(value)

        if self._all_atoms_info is not None:
            payload["allAtomsInfo"] = self._all_atoms_info
        if self._carbon_atoms_info is not None:
            payload["carbonAtomsInfo"] = self._carbon_atoms_info
        if self._nmr_assignments is not None:
            payload["nmrAssignments"] = self._nmr_assignments
        if self._c13predictions is not None:
            payload["c13predictions"] = self._c13predictions

        payload["chosenSpectra"] = self.spectra.build_chosen_spectra()
        if self.source == "bruker":
            payload["exptIdentifiers"] = self.spectra.build_expt_identifiers()
        if self.spectra.has_spectra_with_peaks():
            payload["spectraWithPeaks"] = self.spectra.build_spectra_with_peaks()

        payload.update(self.spectra.build_blocks())

        # Structurally cannot produce an invalid submission: check the
        # required-field contract before returning.
        validate_required(payload, self.source)

        if run_validation:
            ok, messages = validate_payload(payload, validator_path=validator_path)
            if not ok:
                raise ContractError(f"validate_simplenmr_json.py rejected the payload: {messages}")

        return payload
