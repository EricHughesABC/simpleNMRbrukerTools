#!/usr/bin/env python3
"""
run_converter.py - Standalone script to run BrukerToJSONConverter

Place this file in your project root directory and run:
python run_converter.py /path/to/bruker/data
"""
import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Now we can import our modules
from core.json_converter import BrukerToJSONConverter

def main():
    """Main function to run the converter."""
    if len(sys.argv) != 2:
        print("Usage: python run_converter.py <bruker_data_directory>")
        print("Example: python run_converter.py /path/to/your/nmr/data")
        return
    
    data_dir = Path(sys.argv[1])
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        return
    
    print(f"Processing Bruker data directory: {data_dir}")
    
    try:
        # Create converter
        converter = BrukerToJSONConverter(data_dir)
        
        # Find experiments with peaks automatically
        user_selections = {}
        for expt_id, expt_data in converter.bruker_data.items():
            if expt_data.get('haspeaks', False):
                exp_type = expt_data.get('experimentType', 'Unknown')
                if exp_type != 'Unknown':
                    pdata = expt_data.get('pdata', {})
                    proc_folders = pdata.get('procfolders', [])
                    if proc_folders:
                        procno = proc_folders[0].name
                        user_selections[expt_id] = {
                            'experimentType': exp_type,
                            'procno': procno
                        }
                        print(f"✓ Found experiment {expt_id} ({exp_type}) with processed data {procno}")
        
        if not user_selections:
            print("No experiments with peaks found in the directory.")
            print("Make sure your Bruker data contains processed spectra with peak lists.")
            return
        
        print(f"\nConverting {len(user_selections)} experiments to JSON...")
        
        # Convert to JSON
        json_data = converter.convert_to_json(
            user_selections,
            ml_consent=False,
            simulated_annealing=True
        )
        
        # Save to file
        output_file = data_dir.name + "_assignments.json"
        converter.save_json(output_file)
        
        print(f"✓ Conversion complete!")
        print(f"✓ Output saved to: {output_file}")
        print(f"✓ Processed {len(user_selections)} experiments")
        
        # Print summary
        print("\nSummary:")
        for expt_id, selection in user_selections.items():
            exp_type = selection['experimentType']
            procno = selection['procno']
            print(f"  - {expt_id}: {exp_type} (proc {procno})")
            
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()