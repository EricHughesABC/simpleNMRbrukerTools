"""
Integration with the real validate_simplenmr_json.py + simplenmr_input.schema.json
(vendored under simplenmr_builder/vendor/, uploaded 2026-08-27).

The validator script exposes two module-level functions we call directly
rather than guessing at a public API:
  - run_schema_validation(data, schema) -> list[str]   (structural/type)
  - check_hsqc_present(data) -> list[str]              (business rule)

Both lists empty means the payload would pass the server's own checks.
Requires the `jsonschema` package (the vendored script imports it at
module load time and calls sys.exit(2) itself if missing — this module
does not try to swallow that, since it means the environment is
genuinely missing a hard dependency, not something to degrade around).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_PACKAGE_DIR = Path(__file__).parent
DEFAULT_VALIDATOR_PATH = _PACKAGE_DIR / "vendor" / "validate_simplenmr_json.py"
DEFAULT_SCHEMA_PATH = _PACKAGE_DIR / "vendor" / "simplenmr_input.schema.json"


def _load_validator_module(path: Path):
    spec = importlib.util.spec_from_file_location("_vendored_validate_simplenmr_json", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load validator module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_payload(
    payload: dict[str, Any],
    validator_path: str | Path | None = None,
    schema_path: str | Path | None = None,
) -> tuple[bool, list[str]]:
    """
    Returns (valid, messages). If the vendored validator/schema aren't
    present at the resolved paths, returns (True, [warning]) rather than
    silently claiming a clean validation — check `messages`, not just the
    boolean, if you care whether real validation actually ran.
    """
    v_path = Path(validator_path) if validator_path else DEFAULT_VALIDATOR_PATH
    s_path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH

    if not v_path.exists() or not s_path.exists():
        return True, [
            f"validator ({v_path}) or schema ({s_path}) not found — schema validation was SKIPPED, not passed"
        ]

    module = _load_validator_module(v_path)
    schema = json.loads(s_path.read_text(encoding="utf-8"))

    schema_errors = module.run_schema_validation(payload, schema)
    hsqc_errors = module.check_hsqc_present(payload)
    errors = schema_errors + hsqc_errors
    return (len(errors) == 0), errors
