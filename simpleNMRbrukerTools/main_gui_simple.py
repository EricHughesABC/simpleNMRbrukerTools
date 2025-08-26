#!/usr/bin/env python3
"""
main_gui_simple.py - Simplified GUI program without server registration

This is a simpler version for testing and offline use.
It creates the JSON file but doesn't submit to the server.

Usage:
    python main_gui_simple.py
"""
import sys
from pathlib import Path
from typing import Dict, List

# Add src to Python path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

print(f"Using project root: {project_root}")
print(f"Using src path: {src_path}")

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

# Our refactored modules
try:
    from src.core.json_converter import BrukerToJSONConverter
    from config import EXPERIMENT_CONFIGS
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the project root and have the correct directory structure.")
    sys.exit(1)

# Initialize QApplication for GUIDATA
_app = guidata.qapplication()


class BrukerFolderDialog(DataSet):
    """Dialog for selecting Bruker experiment folder."""
    bruker_folder = DirectoryItem("Bruker Data Folder", default=".")


def create_processing_dialog(experiments_with_peaks: Dict[str, List], converter: BrukerToJSONConverter):
    """
    Dynamically create a processing dialog based on available experiments.
    
    Args:
        experiments_with_peaks: Dictionary mapping experiment IDs to available processing folders
        converter: BrukerToJSONConverter instance
        
    Returns:
        DataSet class for the processing dialog
    """
    
    class ProcessingDialog(gds.DataSet):
        """Dialog for selecting experiments and processing options."""
        pass
    
    # Store experiment choice items for later reference
    experiment_choices = {}
    
    # Add experiment selection items
    for expt_id, proc_folders in experiments_with_peaks.items():
        expt_data = converter.bruker_data[expt_id]
        experiment_type = expt_data.get('experimentType', 'Unknown')
        
        if experiment_type == "Unknown":
            continue
        
        # Create list of processing options
        proc_options = [folder.name for folder in proc_folders]
        proc_options.append("SKIP")
        
        # Create choice item
        attr_name = f"expt_{expt_id}"
        choice_item = gdi.ChoiceItem(
            f"{expt_id} - {experiment_type}", 
            proc_options,
            default=0
        )
        
        # Add to class
        setattr(ProcessingDialog, attr_name, choice_item)
        experiment_choices[attr_name] = choice_item
        
        print(f"Added experiment: {expt_id} ({experiment_type})")
    
    # Add processing options
    ProcessingDialog.simulated_annealing = gdi.BoolItem(
        "Use simulated annealing optimization", 
        default=True
    )
    
    ProcessingDialog.ml_consent = gdi.BoolItem(
        "Permit data for ML database", 
        default=False
    )
    
    # Store experiment choices
    ProcessingDialog._experiment_choices = experiment_choices
    
    return ProcessingDialog


def main():
    """Simplified main function."""
    print("Bruker NMR Data Converter - Simple GUI")
    print("=" * 50)
    
    # Step 1: Select folder
    print("1. Select Bruker Data Folder...")
    folder_dialog = BrukerFolderDialog()
    
    if not folder_dialog.edit():
        print("No folder selected. Exiting.")
        return
    
    bruker_data_dir = Path(folder_dialog.bruker_folder)
    print(f"Selected: {bruker_data_dir}")
    
    # Step 2: Load data
    print("\n2. Loading Bruker data...")
    try:
        converter = BrukerToJSONConverter(bruker_data_dir)
        print(f"Found {len(converter.bruker_data.data)} experiments")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Step 3: Find experiments with peaks
    experiments_with_peaks = {}
    for expt_id, expt_data in converter.bruker_data.items():
        if expt_data.get('haspeaks', False):
            exp_type = expt_data.get('experimentType', 'Unknown')
            if exp_type != 'Unknown':
                pdata = expt_data.get('pdata', {})
                proc_folders = []
                for folder in pdata.get('procfolders', []):
                    folder_name = folder.name
                    if pdata.get(folder_name, {}).get('haspeaks', False):
                        proc_folders.append(folder)
                
                if proc_folders:
                    experiments_with_peaks[expt_id] = proc_folders
    
    if not experiments_with_peaks:
        print("No experiments with peaks found!")
        return
    
    print(f"Found {len(experiments_with_peaks)} experiments with peaks")
    
    # Step 4: Show dialog
    print("\n3. Select experiments to process...")
    ProcessingDialog = create_processing_dialog(experiments_with_peaks, converter)
    dialog = ProcessingDialog()
    
    if not dialog.edit():
        print("Cancelled.")
        return
    
    # Step 5: Process selections
    user_selections = {}
    for expt_id in experiments_with_peaks.keys():
        expt_data = converter.bruker_data[expt_id]
        exp_type = expt_data.get('experimentType', 'Unknown')
        
        if exp_type == "Unknown":
            continue
        
        attr_name = f"expt_{expt_id}"
        if hasattr(dialog, attr_name):
            selected_index = getattr(dialog, attr_name)
            choice_item = dialog._experiment_choices[attr_name]
            choices = choice_item.get_prop("data", "choices")
            
            if 0 <= selected_index < len(choices):
                selected_choice = choices[selected_index][1]
                
                if selected_choice != "SKIP":
                    user_selections[expt_id] = {
                        "experimentType": exp_type,
                        "procno": selected_choice
                    }
                    print(f"Selected: {expt_id} ({exp_type}) - {selected_choice}")
    
    if not user_selections:
        print("No experiments selected!")
        return
    
    # Step 6: Convert to JSON
    print(f"\n4. Converting {len(user_selections)} experiments...")
    try:
        json_data = converter.convert_to_json(
            user_expt_selections=user_selections,
            ml_consent=dialog.ml_consent,
            simulated_annealing=dialog.simulated_annealing
        )
        
        # Save file
        output_file = f"{bruker_data_dir.name}_assignments.json"
        converter.save_json(output_file)
        
        print(f"✓ Success! Saved to: {output_file}")
        print(f"✓ ML consent: {dialog.ml_consent}")
        print(f"✓ Simulated annealing: {dialog.simulated_annealing}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDone!")
    input("Press Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")