#!/usr/bin/env python3
"""
validate_simplenmr_json.py

Standalone validator for JSON files intended for simpleNMRtools' /simpleMNOVA
endpoint (submitted by MNova, Bruker, or JEOL/JASON client converters).

Two layers of checking, deliberately kept separate:

  1. STRUCTURAL/TYPE validation against simplenmr_input.schema.json (a JSON
     Schema, draft 2020-12). This covers field presence, envelope shape
     (datatype/count/data), and spectrum-block key patterns.

  2. BUSINESS-RULE validation for the handful of cross-field constraints that
     JSON Schema cannot express cleanly. Currently just one: HSQC must
     actually be present and not exclusively SKIP'd, mirroring the exact
     check core/nmrsolution.py performs server-side (NMRsolution.__init__,
     L61-68) before anything else runs. This check is deliberately a direct
     port of that server logic, not a reinterpretation of it, so a file that
     passes this script should also pass the server's own HSQC check.

Every constraint in both layers traces back to a confirmed finding in
simpleNMR_field_manifest.yaml — nothing here is guessed. Fields the manifest
marked "required: unknown" are intentionally left optional in the schema
rather than enforced, per an explicit decision to tighten only as each is
independently confirmed; see --list-open-items to see what's still pending.

Usage:
    python validate_simplenmr_json.py path/to/submission.json
    python validate_simplenmr_json.py path/to/submission.json --schema path/to/schema.json
    python validate_simplenmr_json.py --list-open-items
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print(
        "ERROR: the 'jsonschema' package is required. Install it with:\n"
        "    pip install jsonschema\n",
        file=sys.stderr,
    )
    sys.exit(2)


DEFAULT_SCHEMA_PATH = Path(__file__).parent / "simplenmr_input.schema.json"

# Mirrors core/nmrsolution.py NMRsolution.__init__ L61-68 exactly.
HSQC_TOKEN = "HSQC"

OPEN_ITEMS = [
    "JEOL SKIP-removal list-mutation bug (simpleNMRjeolTools.py) — not checked by "
    "this script; a JEOL submission could contain a spectrum the user marked SKIP "
    "that leaked through due to the bug. This script has no way to detect that "
    "from the JSON alone, since the leaked entry looks like a normal submission.",
    "JEOL_prediction_used() firing for 'MNOVA Predict' — unresolved design "
    "question about whether the server SHOULD trust submitted c13predictions "
    "for that MNOVAcalcMethod value. This script does not second-guess it.",
    "combine_multiple_nmrExpt_dataframes' exact-value ppm de-duplication when "
    "multiple blocks of the same experiment type are submitted (e.g. HSQC_0 + "
    "HSQC_1) — unresolved whether a tolerance window would better achieve the "
    "intended reconciliation across different-resolution acquisitions. Not "
    "checked here; this script accepts multi-block submissions unconditionally, "
    "matching current server behavior.",
    "Hard-vs-soft requiredness for COSY, HMBC, HSQC_CLIPCOSY, DDEPTCH3ONLY, "
    "H1_1D, H1_pureshift, C13_1D individually — Eric confirmed the PROGRAM runs "
    "without them, but whether any are needed for a GOOD solve (vs. running but "
    "underdetermined) is still open. This script treats all of them as optional, "
    "matching the manifest's current state — expect this list to shrink as "
    "fields move from 'required: unknown' to confirmed.",
    "workingDirectory, workingFilename, subtype, pulsesequence, intrument, "
    "probe, class, origin, spectype, experiment, filename, datafilename, "
    "expt_fn, spectraWithPeaks, carbonCalcPositionsMethod — all still "
    "'required: unknown' or source-specific in the manifest; left optional here.",
]


def load_json_file(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)


def load_schema(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: schema file not found: {path}", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_schema_validation(data: dict, schema: dict) -> list[str]:
    """Returns a list of human-readable structural error messages (empty if valid)."""
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    messages = []
    for err in errors:
        path = ".".join(str(p) for p in err.path) or "(top level)"
        messages.append(f"  [{path}] {err.message}")
    return messages


def check_hsqc_present(data: dict) -> list[str]:
    """
    Direct port of core/nmrsolution.py NMRsolution.__init__ L61-68:

        self.expts_available = set(problemdata_json.dataframes["chosenSpectra"]["expt"])
        if "SKIP" in self.expts_available:
            self.expts_available.remove("SKIP")
        if "HSQC" not in self.expts_available:
            self.fail("<p>HSQC experiment not present</p>")

    The server derives "expt" as the LAST whitespace token of each
    chosenSpectra string value (core/html_from_assignments.py L505-520:
    expt = s.split()[-1]). We replicate that here rather than assuming any
    particular field layout, since the manifest confirms the token count
    and ordering genuinely differs across MNova/Bruker/JEOL.
    """
    errors = []
    chosen = data.get("chosenSpectra", {}).get("data", {})
    if not chosen:
        errors.append(
            "  chosenSpectra is missing or empty — cannot determine whether "
            "HSQC is present. The server will fail with 'HSQC experiment not "
            "present' on this file."
        )
        return errors

    expts_available = set()
    for value in chosen.values():
        if not isinstance(value, str) or not value.strip():
            continue
        expts_available.add(value.split()[-1])

    expts_available.discard("SKIP")

    if HSQC_TOKEN not in expts_available:
        errors.append(
            "  HSQC not present in chosenSpectra (after stripping SKIP entries). "
            "This exactly mirrors core/nmrsolution.py's own check — the server "
            "will fail immediately on this file with 'HSQC experiment not "
            "present'. HSQC is the only experiment type confirmed hard-required "
            "for the program to run at all."
        )

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate a simpleNMR /simpleMNOVA input JSON file against "
        "the manifest-derived schema and the HSQC business rule."
    )
    parser.add_argument(
        "json_file",
        nargs="?",
        type=Path,
        help="Path to the submission JSON file to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to the JSON Schema file (default: {DEFAULT_SCHEMA_PATH.name}, "
        "looked up next to this script).",
    )
    parser.add_argument(
        "--list-open-items",
        action="store_true",
        help="List known contract questions this validator does NOT check, "
        "because the manifest hasn't confirmed the answer yet. Exits without "
        "validating a file.",
    )
    args = parser.parse_args()

    if args.list_open_items:
        print("Open items NOT checked by this validator (see simpleNMR_field_manifest.yaml):\n")
        for i, item in enumerate(OPEN_ITEMS, 1):
            print(f"{i}. {item}\n")
        sys.exit(0)

    if args.json_file is None:
        parser.error("json_file is required unless --list-open-items is given")

    data = load_json_file(args.json_file)
    schema = load_schema(args.schema)

    print(f"Validating: {args.json_file}")
    print(f"Against schema: {args.schema}\n")

    schema_errors = run_schema_validation(data, schema)
    hsqc_errors = check_hsqc_present(data)

    all_errors = schema_errors + hsqc_errors

    if not all_errors:
        print("PASS — no structural or HSQC-requirement errors found.")
        print(
            "\nNote: this does not guarantee a good solve, only a valid "
            "submission. Run with --list-open-items to see confirmed gaps in "
            "current contract knowledge that this validator does not check."
        )
        sys.exit(0)
    else:
        if schema_errors:
            print(f"STRUCTURAL/TYPE errors ({len(schema_errors)}):")
            print("\n".join(schema_errors))
            print()
        if hsqc_errors:
            print(f"BUSINESS-RULE errors ({len(hsqc_errors)}):")
            print("\n".join(hsqc_errors))
            print()
        print(f"FAIL — {len(all_errors)} error(s) found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
