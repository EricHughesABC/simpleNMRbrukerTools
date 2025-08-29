#!/usr/bin/env python3
"""
main_gui.py - Main program with GUIDATA interface for Bruker NMR data conversion

This program provides a GUI interface for selecting Bruker data directories,
choosing experiments to process, and converting them to JSON format.

Dependencies:
- guidata
- PyQt5 (or PySide2)
- All the refactored bruker_nmr modules

Usage:
    python main_gui.py
"""
import os
import sys
import json
import uuid
# import socket
import requests
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
from qtpy.QtWidgets import QProgressDialog, QApplication, QMessageBox
from qtpy.QtCore import Qt

from bruker.api.topspin import Topspin
from bruker.data.nmr import *

import simpleNMRbrukerTools
print(simpleNMRbrukerTools.__version__)

# Import submodules
from simpleNMRbrukerTools import core
from simpleNMRbrukerTools import gui
from simpleNMRbrukerTools import parsers
from simpleNMRbrukerTools import utils

from simpleNMRbrukerTools.core.json_converter import BrukerToJSONConverter
from simpleNMRbrukerTools.core.data_reader import BrukerDataDirectory  
from simpleNMRbrukerTools.config import EXPERIMENT_CONFIGS

# GUIDATA imports
try:
    import guidata
    import guidata.dataset as gds
    import guidata.dataset.dataitems as gdi
    from guidata.dataset.datatypes import DataSet
    from guidata.dataset.dataitems import DirectoryItem
    GUIDATA_AVAILABLE = True
except ImportError:
    print("Error: GUIDATA not available. Please install guidata:")
    print("pip install guidata")
    sys.exit(1)

if GUIDATA_AVAILABLE:
    # import local guidataWarningDialogs
    from simpleNMRbrukerTools.gui.guidataWarningDialogs import WarningDialog, myGUIDATAwarn

class BrukerFolderDialog(DataSet):
    """Dialog for selecting Bruker experiment folder."""
    bruker_folder = DirectoryItem("Bruker Data Folder", default=".")


def create_processing_class(expt_pdata_with_peaks, converter):
    class Processing(gds.DataSet):
        """Example"""
        
        expts = {}
        
        for expt_id, proc_files in expt_pdata_with_peaks.items():
            expt_data = converter.bruker_data[expt_id]
            experiment_type = expt_data.get('experimentType', 'Unknown')
            if experiment_type == "Unknown":
                continue
            
            procnumbers = [proc_file.name for proc_file in proc_files]
            procnumbers.append("SKIP")
            print(expt_id, procnumbers)
            
            expts[f"expt_{expt_id}"] = (gdi.ChoiceItem(f"{expt_id} {experiment_type}", procnumbers))
            locals()[f"expt_{expt_id}"] = expts[f"expt_{expt_id}"]

        simulated_annealing = gdi.BoolItem("Use simulated annealing", default=True)
        ml_consent = gdi.BoolItem("Permit Data to be saved to build Database", default=False)
    
    return Processing

def create_processing_dialog(experiments_with_peaks: Dict[str, List], converter):
    """
    Dynamically create a processing dialog based on available experiments.
    
    Args:
        experiments_with_peaks: Dictionary mapping experiment IDs to available processing folders
        converter: BrukerToJSONConverter instance
        
    Returns:
        DataSet class for the processing dialog
    """
    class Processing(gds.DataSet):
        """Choose Spectra"""
        
        _experiment_choices = {}
        
        for expt_id, proc_files in experiments_with_peaks.items():
            expt_data = converter.bruker_data[expt_id]
            experiment_type = expt_data.get('experimentType', 'Unknown')
            if experiment_type == "Unknown":
                continue
            
            procnumbers = [proc_file.name for proc_file in proc_files]
            procnumbers.append("SKIP")
            print(expt_id, procnumbers)

            _experiment_choices[f"expt_{expt_id}"] = (gdi.ChoiceItem(f"{expt_id} {experiment_type}", procnumbers))
            locals()[f"expt_{expt_id}"] = _experiment_choices[f"expt_{expt_id}"]

        simulated_annealing = gdi.BoolItem("Use simulated annealing", 
                                           default=True,
                                           help="Enable simulated annealing of COSY and HMBC for structure optimization")
        ml_consent = gdi.BoolItem("Permit Data to be saved to build Database", 
                                  default=False,
                                  help="Allow your data to contribute to improving NMR prediction models")
    
    return Processing
 


def check_user_registration() -> bool:
    """
    Check if the user's machine is registered for the service.
    
    Returns:
        True if user can proceed, False otherwise
    """
    try:
        # Generate machine ID (MAC address based)
        mac_based_id = hex(uuid.getnode())
        print(f"Machine ID: {mac_based_id}")
        
        # Prepare request
        json_obj = {"hostname": mac_based_id}
        entry_point = "https://test-simplenmr.pythonanywhere.com/check_machine_learning"
        
        print("Checking user registration...")
        
        # Make the POST request
        response = requests.post(
            entry_point,
            headers={'Content-Type': 'application/json'},
            json=json_obj,
            timeout=100
        )
        
        print(f"Registration check response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                print("Invalid JSON response from server.")
                myGUIDATAwarn("Invalid JSON response from server.")
                return False
            
            status = response_data.get("status", False)
            
            if isinstance(status, str) and status.strip().lower() == "unregistered":
                print("Machine is unregistered. Opening registration page...")
                registration_url = response_data.get("registration_url", "")
                if registration_url:
                    webbrowser.open(registration_url)
                else:
                    print("No registration URL provided.")
                myGUIDATAwarn("No registration URL provided.")
                return False
            
            elif isinstance(status, str) and status.strip().lower() == "registered":
                print("Machine is registered. Proceeding...")
                return True
            
            elif isinstance(status, bool) and not status:
                print("Registration status unclear.")
                myGUIDATAwarn("Registration status unclear.")
                return False
            
        else:
            print(f"Registration check failed: {response.status_code} - {response.text}")
            myGUIDATAwarn(f"Registration check failed: {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        print(f"Network error during registration check: {e}")
        print("Proceeding without registration check...")
        myGUIDATAwarn("Network error during registration check. Proceeding without registration check.")
        return True  # Allow offline usage
    except Exception as e:
        print(f"Error during registration check: {e}")
        myGUIDATAwarn(f"Error during registration check: {e}")
        
    return False


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


def process_user_selections(dialog_instance, experiments_with_peaks: Dict, converter) -> Dict[str, Dict]:
    """
    Process user selections from the dialog.
    
    Args:
        dialog_instance: Instance of the ProcessingDialog
        experiments_with_peaks: Available experiments
        converter: BrukerToJSONConverter instance
        
    Returns:
        Dictionary of user selections for conversion
    """
    user_selections = {}
    
    # Handle both data structures
    if hasattr(converter, 'bruker_data'):
        data_dict = converter.bruker_data.data if hasattr(converter.bruker_data, 'data') else converter.bruker_data
    else:
        data_dict = converter._all_bruker_folders
    
    for expt_id in experiments_with_peaks.keys():
        expt_data = data_dict[expt_id]
        experiment_type = expt_data.get('experimentType', 'Unknown')
        
        if experiment_type == "Unknown":
            continue
        
        attr_name = f"expt_{expt_id}"
        if hasattr(dialog_instance, attr_name):
            selected_index = getattr(dialog_instance, attr_name)
            
            # Get the choice item to access the options
            choice_item = dialog_instance._experiment_choices[attr_name]
            choices = choice_item.get_prop("data", "choices")
            
            # Convert index to actual choice text
            if 0 <= selected_index < len(choices):
                selected_choice = choices[selected_index][1]  # choices is list of (value, label) tuples
                
                print(f"User selected: {expt_id} ({experiment_type}) -> {selected_choice}")
                
                if selected_choice != "SKIP":
                    user_selections[expt_id] = {
                        "experimentType": experiment_type,
                        "procno": selected_choice
                    }
    
    return user_selections


def submit_to_server(json_data: Dict) -> bool:
    """
    Submit the JSON data to the processing server.
    
    Args:
        json_data: The converted JSON data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print("Submitting data to simpleNMR server...")
        
        response = requests.post(
            'https://test-simplenmr.pythonanywhere.com/simpleMNOVA',
            headers={'Content-Type': 'application/json'},
            json=json_data,
            timeout=100
        )
        
        print(f"Server response: {response.status_code}")
        
        if response.status_code == 200:

            # replace dummy_title in response.txt with working_filename from json_data
            workingFilename = json_data["workingFilename"]["data"].get("0", "nmr_analysis_result")
            print(f"Working filename: {workingFilename}")
            response_text = response.text
            print(f"Response text length: {type(response_text)}")
            response_text = response_text.replace("dummy_title", workingFilename)
            print("subtituted for dummy_title")
            # Save response to file
            fn_str = json_data["workingDirectory"]["data"].get("0", ".") 


            fn_path = Path(fn_str, "html")

            print(f"Working directory: {fn_path}, Exists = {fn_path.exists()}")


            if not fn_path.exists():
                fn_path.mkdir(parents=True, exist_ok=True)

            # add filename to path
            fn_path = Path(fn_path, workingFilename + ".html")

            print(f"Saving results to: {fn_path}")
            with open(fn_path, 'w', encoding='utf-8') as f:
                f.write(response_text)

            print(f"Analysis complete! Results saved to '{fn_path}'")

            # Open in browser
            webbrowser.open(f'file://{fn_path}')

            return True
        else:
            print(f"Server error: {response.status_code} - {response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return False
    except Exception as e:
        print(f"Error submitting to simpleNMR server: {e}")
        return False

# import threading
# import webbrowser
# from pathlib import Path
# from typing import Dict
# import requests
# from qtpy.QtWidgets import QProgressDialog, QApplication, QMessageBox
# from qtpy.QtCore import Qt

def submit_to_server(json_data: Dict) -> bool:
    """
    Submit the JSON data to the processing server with progress dialog.
    
    Args:
        json_data: The converted JSON data
        
    Returns:
        True if successful, False otherwise
    """
    
    # Create progress dialog
    progress = QProgressDialog("Submitting data to simpleNMR server...", "Cancel", 0, 0)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)  # Remove cancel button since we can't easily cancel the request
    progress.show()
    
    # Variables to store result
    result = {'success': False, 'error': None, 'finished': False}
    
    def make_request():
        try:
            print("Submitting data to simpleNMR server...")
            
            response = requests.post(
                'https://test-simplenmr.pythonanywhere.com/simpleMNOVA',
                headers={'Content-Type': 'application/json'},
                json=json_data,
                timeout=100
            )
            
            print(f"Server response: {response.status_code}")
            
            if response.status_code == 200:
                # replace dummy_title in response.txt with working_filename from json_data
                workingFilename = json_data["workingFilename"]["data"].get("0", "nmr_analysis_result")
                print(f"Working filename: {workingFilename}")
                response_text = response.text
                print(f"Response text length: {type(response_text)}")
                response_text = response_text.replace("dummy_title", workingFilename)
                print("subtituted for dummy_title")
                
                # Save response to file
                fn_str = json_data["workingDirectory"]["data"].get("0", ".") 
                fn_path = Path(fn_str, "html")

                print(f"Working directory: {fn_path}, Exists = {fn_path.exists()}")

                if not fn_path.exists():
                    fn_path.mkdir(parents=True, exist_ok=True)

                # add filename to path
                fn_path = Path(fn_path, workingFilename + ".html")

                print(f"Saving results to: {fn_path}")
                with open(fn_path, 'w', encoding='utf-8') as f:
                    f.write(response_text)

                print(f"Analysis complete! Results saved to '{fn_path}'")

                # Open in browser
                webbrowser.open(f'file://{fn_path}')

                result['success'] = True
            else:
                error_msg = f"Server error: {response.status_code} - {response.text}"
                print(error_msg)
                result['error'] = error_msg
                
        except requests.RequestException as e:
            error_msg = f"Network error: {e}"
            print(error_msg)
            result['error'] = error_msg
        except Exception as e:
            error_msg = f"Error submitting to simpleNMR server: {e}"
            print(error_msg)
            result['error'] = error_msg
        finally:
            result['finished'] = True
    
    # Start request in background thread
    thread = threading.Thread(target=make_request)
    thread.daemon = True
    thread.start()
    
    # Process events until request is complete
    while not result['finished']:
        QApplication.processEvents()
        thread.join(0.1)  # Check every 100ms
        
        # Update progress dialog text periodically to show it's still working
        if progress.value() % 10 == 0:  # Every ~1 second
            progress.setLabelText("Submitting data to simpleNMR server...")
    
    progress.close()
    
    # Handle the result
    if result['error']:
        # Show error dialog
        QMessageBox.critical(None, "Submission Error", 
                           f"Failed to submit data to server:\n{result['error']}")
        return False
    
    if result['success']:
        # Show success message
        # QMessageBox.information(None, "Success", 
        #                       "Analysis complete! Results have been saved and opened in your browser.")
        print("Analysis complete! Results have been saved and opened in your browser.")

    return result['success']


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

# Initialize QApplication for GUIDATA
_app = guidata.qapplication()








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
        bruker_expt_folder = get_bruker_root_folder_from_identifier(cdataset.getIdentifier())

    print(brukerRootFolder)

    """Main function with GUI interface."""
    print("=" * 60)
    print("Bruker NMR Data Converter - GUI Version")
    print("=" * 60)
    
    # Check user registration
    if not check_user_registration():
        print("\nUnable to verify registration. Please check your internet connection")
        print("   or contact support at simpleNMR@gmail.com for assistance.")
        input("Press Enter to exit...")
        myGUIDATAwarn("Unable to verify registration. Please check your internet connection or contact support.")
        return

    
    print("\n Registration verified. Starting application...")
    
    # Step 1: Select Bruker data folder
    folder_dialog = BrukerFolderDialog(title="Select Bruker Data Folder")
    # set default folder
    folder_dialog.bruker_folder = str(brukerRootFolder)
    
    if not folder_dialog.edit():
        print("No folder selected. Exiting.")
        myGUIDATAwarn("No folder selected. Exiting.")
        return
    
    bruker_data_dir = Path(folder_dialog.bruker_folder)
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
    ProcessingDialog = create_processing_dialog(experiments_with_peaks, converter)
    dialog_instance = ProcessingDialog()
    
    if not dialog_instance.edit():
        print("Dialog cancelled. Exiting.")
        return
    
    # Step 5: Process user selections
    print("\n5. Processing User Selections...")
    user_selections = process_user_selections(dialog_instance, experiments_with_peaks, converter)

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
    ml_consent = dialog_instance.ml_consent
    simulated_annealing = dialog_instance.simulated_annealing

    print(f"  - ML consent: {ml_consent}")
    print(f"  - Simulated annealing: {simulated_annealing}")
    
    # Step 6: Convert to JSON
    print("\n6. Converting to JSON...")
    try:
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
    output_filename = f"{converter.data_directory.name}_assignments.json"
    try:
        converter.save_json(output_filename)
        print(f"JSON file saved: {output_filename}")
    except Exception as e:
        print(f"Warning: Could not save JSON file: {e}")
        myGUIDATAwarn(f"Warning: Could not save JSON file: {e}")
        return
    
    # Step 8: Submit to server for analysis
    print("\n7. Submitting to simpleNMR Server...")
    if submit_to_server(json_data):
        print("Analysis complete! Check the opened browser window for results.")
    else:
        print("Server submission failed, but JSON file was saved locally.")
        print(f"   You can manually submit the file: {output_filename}")
        myGUIDATAwarn("Server submission failed, but JSON file was saved locally.\nYou can manually submit the file.")
        return
    
    # success = submit_to_server(your_json_data)
    # if success:
    #     print("Submission completed successfully")
    # else:
    #     print("Submission failed")

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
        input("\nPress Enter to exit...")

