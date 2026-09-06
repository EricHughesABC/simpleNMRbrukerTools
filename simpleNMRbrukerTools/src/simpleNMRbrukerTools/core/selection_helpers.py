"""
selection_helpers.py

Pure-Python helpers for resolving which Bruker experiments/procnos have
peak data and validating a completed selection — extracted out of
topspin_programs/simpleNMRbruker.py so they're importable WITHOUT that
module's top-level `from bruker.api.topspin import Topspin` /
`from bruker.data.nmr import *`, which only exist inside TopSpin's own
bundled Python and make the whole module unimportable anywhere else,
even for code paths that never touch the Topspin() call.

These three functions never touched the TopSpin API in the first place —
they only ever operated on a plain BrukerToJSONConverter instance and
plain dicts — so this is a pure move, not a rewrite. simpleNMRbruker.py
now imports them from here instead of defining them locally; its own
behavior when run inside TopSpin is unchanged.

Added 2026-09 to support simpleNMRuniversal, which needs to drive this
same selection flow from outside TopSpin (given an arbitrary Bruker
experiment directory already on disk) and cannot import anything that
pulls in the `bruker` package.
"""

from __future__ import annotations

from typing import Dict, List


def find_experiments_with_peaks(converter) -> Dict[str, List]:
    """
    Find experiments that have peak data available.

    Args:
        converter: BrukerToJSONConverter instance

    Returns:
        Dictionary mapping experiment IDs to lists of processing folders with peaks
    """
    experiments_with_peaks = {}

    # Handle both original and refactored data structures
    if hasattr(converter, 'bruker_data'):
        # Refactored structure
        data_dict = converter.bruker_data.data if hasattr(converter.bruker_data, 'data') else converter.bruker_data
    else:
        # Original structure
        data_dict = converter._all_bruker_folders

    for expt_id, expt_data in data_dict.items():
        if not expt_data.get('haspeaks', False):
            continue

        experiment_type = expt_data.get('experimentType', 'Unknown')
        if experiment_type == 'Unknown':
            continue

        # Find processing folders with peaks
        pdata = expt_data.get('pdata', {})
        proc_folders_with_peaks = []

        # Handle different pdata structures
        if 'procfolders' in pdata:
            # Refactored structure
            for folder in pdata.get('procfolders', []):
                folder_name = folder.name if hasattr(folder, 'name') else str(folder)
                proc_data = pdata.get(folder_name, {})

                if proc_data.get('haspeaks', False):
                    proc_folders_with_peaks.append(folder)
        else:
            # Original structure - check for numbered folders
            for key, value in pdata.items():
                if key != 'path' and isinstance(value, dict):
                    if value.get('haspeaks', False):
                        proc_folders_with_peaks.append(key)

        if proc_folders_with_peaks:
            experiments_with_peaks[expt_id] = proc_folders_with_peaks
            print(f"Found experiment {expt_id} ({experiment_type}) with {len(proc_folders_with_peaks)} processed datasets")

    return experiments_with_peaks


def process_user_selections(procno_selections: Dict[str, str], converter) -> Dict[str, Dict]:
    """
    Combine the dialog's {expt_id: procno} selections with each
    experiment's known type into the shape convert_to_json_via_builder()
    expects: {expt_id: {"experimentType": ..., "procno": ...}}.

    ProcnoSelectionDialog.get_selections() already excludes SKIP'd rows
    and returns the chosen procno directly (no index-into-choices-list
    lookup needed, unlike the old guidata ChoiceItem, which stored a
    selected INDEX).
    """
    data_dict = converter.bruker_data.data if hasattr(converter.bruker_data, 'data') else converter.bruker_data

    user_selections = {}
    for expt_id, procno in procno_selections.items():
        expt_data = data_dict[expt_id]
        experiment_type = expt_data.get('experimentType', 'Unknown')
        print(f"User selected: {expt_id} ({experiment_type}) -> {procno}")
        user_selections[expt_id] = {"experimentType": experiment_type, "procno": procno}

    return user_selections


def hsqc_present(user_selections) -> bool:
    """
    Check if HSQC experiment with peaks is present in user selections.

    Args:
        user_selections: {expt_id: {"experimentType": ..., "procno": ...}}

    Returns:
        True if HSQC experiment with peaks is present, False otherwise
    """
    for expt in user_selections.values():
        if expt.get('experimentType') == 'HSQC':
            return True
    return False
