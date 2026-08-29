#!/usr/bin/env python3
"""
main_gui.py - Main program with PyQt/qtpy interface for Bruker NMR data conversion

This program provides a GUI interface for selecting Bruker data directories,
choosing experiments to process, and converting them to JSON format.

Dependencies:
- qtpy + a Qt binding (PySide6) — guidata removed 2026-08-27, see
  simplenmr_builder.gui.procno_selection_dialog for the replacement
- simpleNMRbuilder[gui,viewer] — hard dependency, see below (2026-08-28)
- All the refactored bruker_nmr modules

Usage:
    python main_gui.py
"""
# import os
import sys
import json
import uuid
# import socket
from pathlib import Path
# from typing import Dict, List, Optional, Any
from typing import Dict, List
from qtpy.QtWidgets import QProgressDialog, QApplication, QMessageBox, QFileDialog
from qtpy.QtCore import Qt

from bruker.api.topspin import Topspin
from bruker.data.nmr import *

import simpleNMRbrukerTools
print(simpleNMRbrukerTools.__version__)

SERVERADDRESSLOCAL = "http://localhost:5000/"
SERVERADDRESSPYTHONANYWHERE = "https://test-simplenmr.pythonanywhere.com/"

SERVERADDRESS = SERVERADDRESSPYTHONANYWHERE

# ── simplenmr_builder — hard dependency, 2026-08-28 ──────────────────────
# Previously imported defensively with local fallbacks: ~230 lines of
# duplicated submission/registration code (_local_check_user_registration,
# _local_submit_to_server), kept alive purely to cover "the shared
# library isn't installed." That's exactly the failure mode this project
# has been fixing all along — the original JEOL SKIP-removal bug
# survived unfixed in 7 separate copies of that file for the same
# reason, and a stale local submission.py already caused one real silent
# regression on this project. Fallbacks that exist purely for a missing
# dependency don't get bugfixes and don't get noticed when they drift.
# simplenmr_builder is now a hard dependency here: if it's missing, fail
# loudly and immediately at import time with a clear fix.
try:
    from simplenmr_builder.gui.submission import (
        SubmissionOutcome,
        check_user_registration as _shared_check_user_registration,
        open_result_viewer_subprocess,
        submit_to_server as _shared_submit_to_server,
    )
    from simplenmr_builder.gui.procno_selection_dialog import ProcnoSelectionDialog
except ImportError as e:
    print(
        "ERROR: simplenmr_builder[gui,viewer] is not installed in this "
        "environment. Install it with:\n"
        '    pip install -e "<path-to-simpleNMRbuilder>[gui,viewer]"\n'
        f"\nUnderlying import error: {e}"
    )
    sys.exit(1)

from simpleNMRbrukerTools.core.json_converter import BrukerToJSONConverter
# from simpleNMRbrukerTools.core.data_reader import BrukerDataDirectory  
# from simpleNMRbrukerTools.config import EXPERIMENT_CONFIGS


def myGUIDATAwarn(message: str, title: str = "Warning") -> None:
    """Plain QMessageBox warning dialog — no guidata dependency. Kept
    under its original name since it's called from many places in this
    file; only the implementation changed."""
    QMessageBox.warning(None, title, message)
 


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

    Much simpler than the original: ProcnoSelectionDialog.get_selections()
    already excludes SKIP'd rows and returns the chosen procno directly
    (no index-into-choices-list lookup needed, unlike the old
    guidata ChoiceItem, which stored a selected INDEX).
    """
    data_dict = converter.bruker_data.data if hasattr(converter.bruker_data, 'data') else converter.bruker_data

    user_selections = {}
    for expt_id, procno in procno_selections.items():
        expt_data = data_dict[expt_id]
        experiment_type = expt_data.get('experimentType', 'Unknown')
        print(f"User selected: {expt_id} ({experiment_type}) -> {procno}")
        user_selections[expt_id] = {"experimentType": experiment_type, "procno": procno}

    return user_selections


def check_user_registration() -> bool:
    """Wraps the shared simplenmr_builder.gui.submission.check_user_registration
    with Bruker's server address."""
    return _shared_check_user_registration(SERVERADDRESS + "check_machine_learning")


def submit_to_server(json_data: Dict):
    """Wraps the shared simplenmr_builder.gui.submission.submit_to_server
    with Bruker's server address. Returns a SubmissionResult — real
    outcome classification (success / diagnostic report / registration
    required or expired / error), and results open in the shared PyQt
    viewer rather than the system web browser."""
    return _shared_submit_to_server(json_data, SERVERADDRESS + "simpleMNOVA")


def get_bruker_root_folder_from_identifier(path):
    """
    Check if 'pdata' is in the path, and return the path up to the parent of pdata's parent-1.
    """
    path = Path(path)
    parts = path.parts
    
    if 'pdata' in parts:
        pdata_index = parts.index('pdata')
        # Go back one more level (skip the parent of pdata too)
        return Path(*parts[:pdata_index-1])
    
    return None

def hsqc_present(user_selections):
    """
    Check if HSQC experiment with peaks is present in user selections.
    
    Args:
        user_selections: List of user-selected experiments
        
    Returns:
        True if HSQC experiment with peaks is present, False otherwise
    """
    for expt in user_selections.values():
        if expt.get('experimentType') == 'HSQC':
            return True
    return False

# Initialize QApplication
_app = QApplication.instance() or QApplication(sys.argv)

def main():

    top = Topspin()
    dp = top.getDataProvider()
    cdataset = dp.getCurrentDataset()
    print(type(cdataset), type(dp), type(top))

    brukerRootFolder = Path()
    if isinstance(cdataset, type(None)):
        print("Please load a data set that you are working on into Topspin")
    else:
        brukerRootFolder = get_bruker_root_folder_from_identifier(cdataset.getIdentifier())
        # bruker_expt_folder = get_bruker_root_folder_from_identifier(cdataset.getIdentifier())

    print(brukerRootFolder)
    
    # Check user registration
    if not check_user_registration():
        print("\nUnable to verify registration. Please check your internet connection")
        print("   or contact support at simpleNMR@gmail.com for assistance.")
        input("Press Enter to exit...")
        myGUIDATAwarn("Unable to verify registration. Please check your internet connection or contact support.")
        return
    
    print("\n Registration verified. Starting application...")
    
    # Step 1: Select Bruker data folder
    selected_dir = QFileDialog.getExistingDirectory(
        None, "Select Bruker Data Folder", str(brukerRootFolder)
    )

    if not selected_dir:
        print("No folder selected. Exiting.")
        myGUIDATAwarn("No folder selected. Exiting.")
        return

    bruker_data_dir = Path(selected_dir)
    print(f"Selected folder: {bruker_data_dir}")
    
    if not bruker_data_dir.exists():
        print(f"Error: Directory does not exist: {bruker_data_dir}")
        myGUIDATAwarn(f"Error: Directory does not exist: {bruker_data_dir}")
        return
    
    # Step 2: Load and analyze Bruker data
    print("\n2. Analyzing Bruker Data...")
    try:
        converter = BrukerToJSONConverter(bruker_data_dir)
        # Handle both data structures
        if hasattr(converter, 'bruker_data'):
            data_count = len(converter.bruker_data.data if hasattr(converter.bruker_data, 'data') else converter.bruker_data)
        else:
            data_count = len(converter._all_bruker_folders)
        print(f"Found {data_count} experiment folders")
    except Exception as e:
        print(f"Error loading Bruker data: {e}")
        myGUIDATAwarn(f"Error loading Bruker data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Find experiments with peaks
    print("\n3. Finding Experiments with Peak Data...")
    experiments_with_peaks = find_experiments_with_peaks(converter)
    
    if not experiments_with_peaks:
        print("No experiments with peak data found.")
        print("   Make sure your data contains processed spectra with peak lists.")
        myGUIDATAwarn("No experiments with peak data found.\n   Make sure your data contains processed spectra with peak lists.")
        return
    
    print(f"Found {len(experiments_with_peaks)} experiments with peak data")
    
    # check if hsqc expt found in experiments_with_peaks
    hsqc_with_peaks = False
    for expt_id, proc_folders in experiments_with_peaks.items():
        # find id in coverter
        expt = converter.bruker_data[expt_id]
        if expt["experimentType"] == "HSQC":
            print(f"Found HSQC experiment in  {expt_id} with {len(proc_folders)} processing folders")
            hsqc_with_peaks = True
            break

    if not hsqc_with_peaks:
        print("No HSQC experiments found.")
        myGUIDATAwarn("No HSQC experiments found.")
        return

    # Step 4: Create and show processing dialog
    print("\n4. Experiment Selection Dialog")
    dialog_entries = {}
    for expt_id, proc_files in experiments_with_peaks.items():
        expt_data = converter.bruker_data[expt_id]
        experiment_type = expt_data.get('experimentType', 'Unknown')
        if experiment_type == "Unknown":
            continue
        procnumbers = [proc_file.name for proc_file in proc_files]
        print(expt_id, procnumbers + ["SKIP"])
        dialog_entries[expt_id] = {
            "label": f"{expt_id} {experiment_type}",
            "procnos": procnumbers,
        }

    dialog_instance = ProcnoSelectionDialog(dialog_entries)

    if dialog_instance.exec() != ProcnoSelectionDialog.Accepted:
        print("Dialog cancelled. Exiting.")
        return

    # Step 5: Process user selections
    print("\n5. Processing User Selections...")
    user_selections = process_user_selections(dialog_instance.get_selections(), converter)

    if not user_selections:
        print("No experiments selected for processing.")
        myGUIDATAwarn("No experiments selected for processing.")
        return

    elif not hsqc_present(user_selections):
        print("No HSQC experiment with peaks selected for processing.")
        myGUIDATAwarn("No HSQC experiment with peaks selected for processing.")
        return

    # to be completed
    # check if C13_!D selected that the number of peaks is less than or equal to the number of carbons in the molecule
    # check if the number of CH and CH3 peaks in the HSQC experiment is consistent with the number of CH and CH3 groups in the molecule
    # check if the number of CH2 peaks in the HSQC experiment is consistent with the number of CH2 groups in the molecule
    

    print(f"Selected {len(user_selections)} experiments for processing")
    # myGUIDATAwarn(f"Selected {len(user_selections)} experiments for processing")

    # Get processing options
    simulated_annealing, ml_consent = dialog_instance.get_processing_options()

    print(f"  - ML consent: {ml_consent}")
    print(f"  - Simulated annealing: {simulated_annealing}")
    
    # Step 6: Convert to JSON
    print("\n6. Converting to JSON...")
    try:
        if getattr(converter, "convert_to_json_via_builder", None) is not None:
            try:
                json_data = converter.convert_to_json_via_builder(
                    user_expt_selections=user_selections,
                    ml_consent=ml_consent,
                    simulated_annealing=simulated_annealing,
                )
            except Exception as builder_exc:
                # Only ContractError-family exceptions represent a real,
                # specific reason the submission itself is invalid (missing
                # required field, no HSQC, unrecognized experiment-type
                # token). Anything else (e.g. simplenmr_builder not
                # actually importable despite the attribute existing) falls
                # back to the original hand-rolled path below rather than
                # aborting the whole run.
                from simplenmr_builder import ContractError

                if isinstance(builder_exc, ContractError):
                    print(f"Error during JSON conversion: {builder_exc}")
                    myGUIDATAwarn(
                        f"The data could not be validated for submission:\n\n{builder_exc}"
                    )
                    return
                raise
        else:
            print(
                "WARNING: simplenmr_builder is not available - falling back to the "
                "original JSON construction with no pre-submission validation."
            )
            json_data = converter.convert_to_json(
                user_expt_selections=user_selections,
                ml_consent=ml_consent,
                simulated_annealing=simulated_annealing
            )
        print("JSON conversion complete")
    except Exception as e:
        print(f"Error during JSON conversion: {e}")
        myGUIDATAwarn(f"Error during JSON conversion: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 7: Save JSON file locally
    output_filename = Path(converter.data_directory, f"{converter.data_directory.name}_assignments.json")
    try:
        converter.save_json(output_filename)
        print(f"JSON file saved: {output_filename}")
    except Exception as e:
        print(f"Warning: Could not save JSON file: {e}")
        myGUIDATAwarn(f"Warning: Could not save JSON file: {e}")
        return
    
    # check if the molfile string is greater than 0:  ie a valid molfile was found in the topspin dataset
    print("Checking for valid molfile in JSON data...")
    print("json_data keys:", json_data.keys())
    if  "molfile" not in json_data :
        print("Warning: No valid molfile found.")
        myGUIDATAwarn("Warning: No valid molfile found.")
        return

    # Step 8: Submit to server for analysis
    print("\n7. Submitting to simpleNMR Server...")
    submission = submit_to_server(json_data)

    if submission.outcome == SubmissionOutcome.SUCCESS:
        print("Analysis complete! Opening results viewer...")
        # Launched as a SEPARATE process, not imported in-process -
        # guidata is gone now (see procno_selection_dialog.py), but
        # this remains cheap insurance against any future PyQt5
        # dependency causing the same class of Qt-binding collision.
        #
        # wait=True: blocks here until the viewer window is closed,
        # so this script's own lifetime visibly tracks the viewer's
        # rather than exiting immediately while a detached process
        # keeps running. html_viewer.py's __main__ force-exits
        # cleanly the moment its window closes (see its os._exit()
        # call), so this returns promptly with no manual Ctrl-C
        # needed — confirmed 2026-08-27 this combination fixes both
        # the "program exits while the viewer is still coming up"
        # and "have to Ctrl-C to actually close it" complaints.
        open_result_viewer_subprocess(submission, wait=True)
        return
    elif submission.outcome == SubmissionOutcome.DIAGNOSTIC_HTML:
        print(
            f"Server returned a diagnostic report (status {submission.status_code}). "
            "Opening it in the viewer..."
        )
        open_result_viewer_subprocess(submission, wait=True)
        return
    else:
        # submit_to_server() has already shown the appropriate dialog
        # (network error / server error / registration required or
        # expired) - nothing further to do here.
        print(f"Server submission did not succeed: {submission.outcome.value}")
        return
    

    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    
    # # Keep window open
    # input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        myGUIDATAwarn(f"Unexpected error: \n {e}")
        import traceback
        traceback.print_exc()

