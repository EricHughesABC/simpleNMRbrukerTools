import json
import os
import sys
import requests
import webbrowser
import uuid
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import socket

import guidata
import guidata.dataset as gds
import guidata.dataset.dataitems as gdi
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import DirectoryItem

# Import RDKit for mol file processing
try:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    print("Warning: RDKit not available. Mol file processing will be disabled.")
    RDKIT_AVAILABLE = False

# Import your existing BrukerDataDirectory class
from readBrukerSimpleNMR import BrukerDataDirectory, experiments


# Note: the following line is not required if a QApplication has already been created
_app = guidata.qapplication()

class BrukerFolderDialog(DataSet):
    """Select Bruker experiment folder"""
    bruker_folder = DirectoryItem("Bruker Folder", default=".")




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




class BrukerToJSONConverter:
    """
    Converts Bruker NMR data to JSON format similar to MNova output.
    Includes mol file processing using RDKit.
    """
    
    def __init__(self, data_directory: Union[str, Path], smiles: str = None, molfile_content: str = None):
        self.data_directory = Path(data_directory)
        self.smiles = smiles
        self.molfile_content = molfile_content
        
        # Mol file processing attributes
        self.mol_files = []
        self.selected_mol_file = None
        self.rdkit_mol = None
        
        # Initialize the Bruker data reader
        self.bruker_data = BrukerDataDirectory(data_directory, experiments)
        
        # Initialize the JSON structure
        self.json_data = {}
        
        # Process mol file if available and RDKit is installed
        if RDKIT_AVAILABLE:
            self._process_mol_files()
    
    def find_mol_files(self) -> List[Path]:
        """Find all .mol files in the directory."""
        self.mol_files = list(self.data_directory.glob("*.mol"))
        print(f"Found {len(self.mol_files)} mol file(s): {[f.name for f in self.mol_files]}")
        return self.mol_files
    
    def select_mol_file(self, index: int = 0) -> Optional[Path]:
        """Select a mol file to use. Default is the first one found."""
        if not self.mol_files:
            self.find_mol_files()
        
        if not self.mol_files:
            print("No mol files found in the directory.")
            return None
        
        if len(self.mol_files) > 1:
            print(f"Multiple mol files found. Using the first one: {self.mol_files[0].name}")
            print(f"Available files: {[f.name for f in self.mol_files]}")
        
        self.selected_mol_file = self.mol_files[index]
        print(f"Selected mol file: {self.selected_mol_file.name}")
        return self.selected_mol_file
    
    def load_mol_file(self) -> bool:
        """Load the selected mol file using RDKit and read content."""
        if not RDKIT_AVAILABLE:
            print("RDKit not available. Cannot process mol files.")
            return False
            
        if not self.selected_mol_file:
            print("No mol file selected.")
            return False
        
        try:
            # Read the mol file content as text
            with open(self.selected_mol_file, 'r', encoding='utf-8') as f:
                self.molfile_content = f.read()
            
            # Load with RDKit
            self.rdkit_mol = Chem.MolFromMolFile(str(self.selected_mol_file))
            
            if self.rdkit_mol is None:
                print(f"Failed to parse mol file: {self.selected_mol_file}")
                return False
            
            print(f"Successfully loaded mol file: {self.selected_mol_file.name}")
            print(f"Molecule has {self.rdkit_mol.GetNumAtoms()} atoms")
            return True
            
        except Exception as e:
            print(f"Error loading mol file: {e}")
            return False
    
    def generate_smiles_from_mol(self) -> str:
        """Generate SMILES string from the loaded RDKit molecule."""
        if not RDKIT_AVAILABLE or not self.rdkit_mol:
            return self.smiles or ""
        
        try:
            generated_smiles = Chem.MolToSmiles(self.rdkit_mol)
            print(f"Generated SMILES from mol file: {generated_smiles}")
            
            # Use generated SMILES if no SMILES was provided
            if not self.smiles:
                self.smiles = generated_smiles
            elif self.smiles != generated_smiles:
                print(f"Note: Provided SMILES ({self.smiles}) differs from generated SMILES ({generated_smiles})")
                print("Using provided SMILES.")
            
            return self.smiles
        except Exception as e:
            print(f"Error generating SMILES: {e}")
            return self.smiles or ""
    
    def count_hydrogens_on_atom(self, atom) -> int:
        """Count the number of hydrogens on a given atom."""
        return atom.GetTotalNumHs()
    
    def create_all_atoms_info_from_mol(self) -> Dict:
        """Create the allAtomsInfo structure from the RDKit molecule."""
        if not RDKIT_AVAILABLE or not self.rdkit_mol:
            return {"datatype": "allAtomsInfo", "data": {}, "count": 0}
        
        all_atoms_data = {
            "datatype": "allAtomsInfo",
            "data": {},
            "count": self.rdkit_mol.GetNumAtoms()
        }
        
        for atom_idx, atom in enumerate(self.rdkit_mol.GetAtoms()):
            atom_info = {
                "atom_idx": atom_idx,
                "id": atom_idx,
                "atomNumber": str(atom_idx + 1),  # 1-based numbering as string
                "symbol": atom.GetSymbol(),
                "numProtons": self.count_hydrogens_on_atom(atom)
            }
            all_atoms_data["data"][str(atom_idx)] = atom_info
        
        return all_atoms_data
    
    def create_carbon_atoms_info_from_mol(self) -> Dict:
        """Create the carbonAtomsInfo structure from the RDKit molecule."""
        if not RDKIT_AVAILABLE or not self.rdkit_mol:
            return {"datatype": "carbonAtomsInfo", "data": {}, "count": 0}
        
        carbon_atoms_data = {
            "datatype": "carbonAtomsInfo",
            "data": {},
            "count": 0
        }
        
        carbon_count = 0
        for atom_idx, atom in enumerate(self.rdkit_mol.GetAtoms()):
            if atom.GetSymbol() == 'C':
                atom_info = {
                    "atom_idx": atom_idx,
                    "id": atom_idx,
                    "atomNumber": str(atom_idx + 1),  # 1-based numbering as string
                    "symbol": "C",
                    "numProtons": self.count_hydrogens_on_atom(atom)
                }
                carbon_atoms_data["data"][str(atom_idx)] = atom_info
                carbon_count += 1
        
        carbon_atoms_data["count"] = carbon_count
        return carbon_atoms_data
    
    def _process_mol_files(self):
        """Process mol files in the directory."""
        if not RDKIT_AVAILABLE:
            return
            
        self.find_mol_files()
        if self.select_mol_file():
            if self.load_mol_file():
                self.generate_smiles_from_mol()
        
    def convert_to_json(self, user_expt_selections: Dict, ml_consent=False, simulated_annealing=False) -> Dict[str, Any]:
        """
        Main method to convert Bruker data to JSON format.
        """
        # Add basic molecular information
        self._add_molecular_info()
        
        # Add system information
        self._add_system_info()
        
        # Add atom information (placeholder for now)
        self._add_atom_info()
        
        # Add NMR spectra data
        self._add_nmr_spectra(user_expt_selections)
        
        # Add experiment choices and settings
        self._add_experiment_settings()
        
        # Add processing parameters
        self._add_processing_parameters()

        self._add_ml_consent(ml_consent)

        self._add_simulated_annealing(simulated_annealing)
        
        return self.json_data
    
    def _add_ml_consent(self, ml_consent: bool):
        """Add ML consent information."""
        self.json_data["ml_consent"] = {
            "datatype": "ml_consent",
            "count": 1,
            "data": {"0": ml_consent}
        }

    def _add_simulated_annealing(self, simulated_aneealing: bool):
        """Add simulated annealing information."""
        self.json_data["simulatedAnnealing"] = {
            "datatype": "simulatedAnnealing",
            "count": 1,
            "data": {"0": simulated_aneealing}
        }   


    
    def _add_molecular_info(self):
        """Add SMILES and molfile information."""
        if self.smiles:
            self.json_data["smiles"] = {
                "datatype": "smiles",
                "count": 1,
                "data": {"0": self.smiles}
            }
        
        if self.molfile_content:
            self.json_data["molfile"] = {
                "datatype": "molfile",
                "count": 1,
                "data": {"0": self.molfile_content}
            }
    
    def _add_system_info(self):
        """Add system and hostname information."""
        hostname = socket.gethostname()
        hostname = hex(uuid.getnode())
        self.json_data["hostname"] = {
            "datatype": "hostname",
            "count": 1,
            "data": {"0": hostname}
        }
        
        # Add working directory and filename
        self.json_data["workingDirectory"] = {
            "datatype": "workingDirectory",
            "count": 1,
            "data": {"0": str(self.data_directory.absolute()).replace("\\", "/")  # Ensure consistent path format
            }
        }
        
        self.json_data["workingFilename"] = {
            "datatype": "workingFilename",
            "count": 1,
            "data": {"0": self.data_directory.name}
        }
    
    def _add_atom_info(self):
        """Add atom information from mol file or placeholders."""
        if RDKIT_AVAILABLE and self.rdkit_mol:
            # Use RDKit molecule to create atom info
            self.json_data["allAtomsInfo"] = self.create_all_atoms_info_from_mol()
            self.json_data["carbonAtomsInfo"] = self.create_carbon_atoms_info_from_mol()
            print(f"Created atom info from mol file: {self.json_data['allAtomsInfo']['count']} total atoms, {self.json_data['carbonAtomsInfo']['count']} carbon atoms")
        else:
            # Use placeholder structures
            self.json_data["allAtomsInfo"] = {
                "datatype": "allAtomsInfo",
                "data": {},
                "count": 0
            }
            
            self.json_data["carbonAtomsInfo"] = {
                "datatype": "carbonAtomsInfo",
                "data": {},
                "count": 0
            }
            print("No mol file available or RDKit not installed. Using placeholder atom info.")
        
        # Placeholder for NMR assignments
        self.json_data["nmrAssignments"] = {
            "datatype": "nmrAssignments",
            "count": 0,
            "data": {}
        }
        
        self.json_data["c13predictions"] = {
            "datatype": "c13predictions",
            "count": 0,
            "data": {}
        }

    def _add_nmr_spectra(self, user_expt_selections: Dict) -> None:
        """Convert Bruker NMR spectra to JSON format."""
        chosen_spectra = []
        spectrum_counter = 0
        
        expt_dientifiers = []
        for expt_id, expt_selections_values in user_expt_selections.items():

            exp_type = expt_selections_values.get("experimentType", "Unknown")
            print(f"Processing experiment {expt_id} with type {exp_type}")
            procno = expt_selections_values["procno"]

            expt_data = self.bruker_data.get(expt_id, {})
            # exp_type = expt_data.get("experimentType", "Unknown")
            pulseprogram = expt_data.get("pulseprogram", "unknown")
            nuclei = expt_data.get("nuclei", ["Unknown"])
            dimensions = expt_data.get("dimensions", 1)

            
            # Create spectrum identifier
            # change this to use the experimentType and an incrementing counter

            if exp_type == "Unknown":
                exp_type = "SKIP"

            # count the number of times exp_type appears in expt_dientifiers
            exp_type_count = expt_dientifiers.count(exp_type)
            expt_dientifiers.append(exp_type)
            spectrum_id = f"{exp_type}_{exp_type_count}"

            if dimensions == 1:
                nucleus_str = nuclei[0] if nuclei else "Unknown"
                # spectrum_id = f"{expt_id}.fid_{spectrum_counter}"
            else:
                nucleus_str = f"[{', '.join(nuclei)}]"
                # spectrum_id = f"{expt_id}.ser_{spectrum_counter}"
            
            # Create spectrum entry
            spectrum_data = self._create_spectrum_entry(expt_data, spectrum_id, procno)
            
            # Add to main JSON data
            self.json_data[spectrum_id] = spectrum_data
            
            # Add to chosen spectra list
            skip_status = "SKIP" if exp_type == "Unknown" else exp_type
            chosen_entry = f"{nucleus_str} {dimensions}D {pulseprogram} {spectrum_id} {skip_status}"
            chosen_spectra.append(chosen_entry)
            
            spectrum_counter += 1
        
        # Add chosen spectra
        self.json_data["chosenSpectra"] = {
            "datatype": "chosenSpectra",
            "count": len(chosen_spectra),
            "data": {str(i): spec for i, spec in enumerate(chosen_spectra)}
        }
        
        # Add experiment identifiers
        exp_identifiers = []
        for expt_id, expt_data in self.bruker_data.items():
            exp_type = expt_data.get("experimentType", "SKIP")
            exp_identifiers.append(exp_type)
        
        self.json_data["exptIdentifiers"] = {
            "count": len(exp_identifiers),
            "datatype": "exptIdentifiers",
            "data": {str(i): exp_id for i, exp_id in enumerate(exp_identifiers)}
        }
    
    def _create_spectrum_entry(self, expt_data: Dict, spectrum_id: str, procno: str) -> Dict:
        """Create a spectrum entry in the JSON format."""
        nuclei = expt_data.get("nuclei", ["Unknown"])
        dimensions = expt_data.get("dimensions", 1)
        exp_type = expt_data.get("experimentType", "Unknown")
        
        # Get acquisition parameters
        acqu = expt_data.get("acqu", {})
        acqu2 = expt_data.get("acqu2", {})
        
        # Basic spectrum structure
        spectrum_entry = {
            "datatype": "nmrspectrum",
            "origin": "Bruker XWIN-NMR",
            "type": "2D" if dimensions == 2 else "1D",
            "subtype": self._get_spectrum_subtype(nuclei, exp_type),
            "experimenttype": self._get_experiment_type_string(exp_type, dimensions),
            "experiment": exp_type if exp_type != "Unknown" else "1D",
            "class": "",
            "spectype": "",
            "pulsesequence": expt_data.get("pulseprogram", "unknown"),
            "intrument": "Avance",  # Default, could be extracted from acqu
            "probe": self._get_probe_info(acqu),
            "datafilename": str(expt_data.get("path", "")),
            "nucleus": nuclei[0] if len(nuclei) == 1 else str(nuclei),
            "specfrequency": self._get_spec_frequency(acqu, acqu2, dimensions),
        }
    

        # Add peaks and integrals from peaklist if available
        if "peaklist" in expt_data and not expt_data["pdata"][procno]["peaklist"].empty:
            peaks_data, _ = self._convert_peaklist_to_json(expt_data["pdata"][procno]["peaklist"], dimensions)
            spectrum_entry["peaks"] = peaks_data
        else:
            spectrum_entry["peaks"] = {"datatype": "peaks", "data": {}, "count": 0}
        
        # Add integrals for 2D experiments
        if dimensions == 2 and "hasIntegrals" in expt_data and not expt_data["pdata"][procno]["integrals"].empty:
            integrals_data = self._convert_2d_integrals_to_json(expt_data["pdata"][procno]["integrals"])
            spectrum_entry["integrals"] = integrals_data
        else:
            spectrum_entry["integrals"] = {"datatype": "integrals", "count": 0, "normValue": 1, "data": {}}
        
        # Empty multiplets for now
        spectrum_entry["multiplets"] = {
            "datatype": "multiplets",
            "normValue": 1,
            "data": {},
            "count": 0
        }
        
        # Add filename if it's a known experiment type
        if exp_type != "Unknown":
            spectrum_entry["filename"] = spectrum_id
        
        return spectrum_entry
    
    def _get_spectrum_subtype(self, nuclei: List[str], exp_type: str) -> str:
        """Get the spectrum subtype string."""
        if len(nuclei) == 1:
            return nuclei[0]
        elif len(nuclei) == 2:
            if exp_type == "COSY":
                return f"{nuclei[0]}{nuclei[1]}, COSY"
            elif exp_type == "HSQC":
                return f"{nuclei[1]}{nuclei[0]}, HSQC-EDITED"
            elif exp_type == "HMBC":
                return f"{nuclei[1]}{nuclei[0]}, HMBC"
            else:
                return f"{nuclei[1]}{nuclei[0]}, {exp_type}"
        else:
            return "Unknown"
    
    def _get_experiment_type_string(self, exp_type: str, dimensions: int) -> str:
        """Get the experiment type string."""
        if dimensions == 2:
            return f"2D-{exp_type}" if exp_type != "Unknown" else "2D"
        else:
            return "1D"
    
    def _get_probe_info(self, acqu: Dict) -> str:
        """Extract probe information from acquisition parameters."""
        probhd = acqu.get("PROBHD", "Unknown probe")
        return str(probhd)
    
    def _get_spec_frequency(self, acqu: Dict, acqu2: Dict, dimensions: int) -> Union[float, str]:
        """Get spectrometer frequency."""
        if dimensions == 1:
            return acqu.get("BF1", 0.0)
        else:
            bf1 = acqu.get("BF1", 0.0)
            bf2 = acqu2.get("BF1", 0.0) if acqu2 else 0.0
            return f"[{bf2}, {bf1}]"
    
    def _convert_peaklist_to_json(self, peaklist_df, dimensions: int) -> tuple:
        """Convert pandas DataFrame peaklist to JSON format."""
        peaks_data = {"datatype": "peaks", "data": {}, "count": len(peaklist_df)}
        integrals_data = {"datatype": "integrals", "count": 0, "normValue": 1, "data": {}}
        
        for idx, row in peaklist_df.iterrows():
            peak_entry = {
                "intensity": float(row.get("intensity", 0.0)),
                "type": int(row.get("type", 0)),
                "annotation": str(row.get("annotation", ""))
            }
            
            if dimensions == 1:
                peak_entry["delta1"] = float(row.get("ppm", 0.0))
                peak_entry["delta2"] = 0
            else:
                peak_entry["delta1"] = float(row.get("f1_ppm", 0.0))
                peak_entry["delta2"] = float(row.get("f2_ppm", 0.0))
            
            peaks_data["data"][str(idx)] = peak_entry
        
        return peaks_data, integrals_data
    
    def _convert_2d_integrals_to_json(self, integrals_df) -> Dict:
        """Convert 2D integrals pandas DataFrame to JSON format."""
        if integrals_df is None or integrals_df.empty:
            return {"datatype": "integrals", "count": 0, "normValue": 1, "data": {}}
        
        integrals_data = {
            "datatype": "integrals",
            "count": len(integrals_df),
            "normValue": 1,
            "data": {}
        }
        
        for idx, row in integrals_df.iterrows():
            integral_entry = {
                "intensity": float(row.get("integral", 0.0)),
                "rangeMin1": float(row.get("F1_row2_ppm", 0.0)),  # F1 dimension min
                "rangeMin2": float(row.get("F2_col1_ppm", 0.0)),  # F2 dimension min
                "rangeMax1": float(row.get("F1_row1_ppm", 0.0)),  # F1 dimension max
                "rangeMax2": float(row.get("F2_col2_ppm", 0.0)),  # F2 dimension max
                "delta1": float(row.get("f1_ppm", 0.0)),          # F1 center (lowercase)
                "delta2": float(row.get("f2_ppm", 0.0)),          # F2 center (lowercase)
                "type": 0
            }
            
            integrals_data["data"][str(idx)] = integral_entry
        
        return integrals_data
    
    def _add_experiment_settings(self):
        """Add experiment-specific settings."""
        # Add spectra with peaks
        spectra_with_peaks = []
        for expt_id, expt_data in self.bruker_data.items():
            nuclei = expt_data.get("nuclei", ["Unknown"])
            dimensions = expt_data.get("dimensions", 1)
            pulseprogram = expt_data.get("pulseprogram", "unknown")
            exp_type = expt_data.get("experimentType", "Unknown")
            
            if dimensions == 1:
                nucleus_str = f"{nuclei[0]} 1D"
            else:
                nucleus_str = f"[{', '.join(nuclei)}] {exp_type}"
            
            spectrum_name = f"{nucleus_str} {pulseprogram} {expt_id}.{'fid' if dimensions == 1 else 'ser'}_0"
            # add to the list if it has peaks
            if "peaklist" in expt_data and not expt_data["peaklist"].empty:
                # Check if there are peaks
                if not expt_data["peaklist"].empty:
                    # Add to spectra with peaks list
                    spectra_with_peaks.append(spectrum_name)
        
        self.json_data["spectraWithPeaks"] = {
            "datatype": "spectraWithPeaks",
            "count": len(spectra_with_peaks),
            "data": {str(i): spec for i, spec in enumerate(spectra_with_peaks)}
        }
    
    def _add_processing_parameters(self):
        """Add processing and calculation parameters."""
        # Default processing parameters
        self.json_data["carbonCalcPositionsMethod"] = {
            "datatype": "carbonCalcPositionsMethod",
            "count": 1,
            "data": {"0": "Calculated Positions"}
        }
        
        self.json_data["MNOVAcalcMethod"] = {
            "datatype": "MNOVAcalcMethod",
            "count": 1,
            "data": {"0": "NMRSHIFTDB2 Predict"}
        }
        
        # Simulated annealing parameters
        self.json_data["simulatedAnnealing"] = {
            "datatype": "simulatedAnnealing",
            "count": 1,
            "data": {"0": True}
        }
        
        self.json_data["randomizeStart"] = {
            "datatype": "randomizeStart",
            "count": 1,
            "data": {"0": False}
        }
        
        self.json_data["startingTemperature"] = {
            "datatype": "startingTemperature",
            "count": 1,
            "data": {"0": 1000}
        }
        
        self.json_data["endingTemperature"] = {
            "datatype": "endingTemperature",
            "count": 1,
            "data": {"0": 0.1}
        }
        
        self.json_data["coolingRate"] = {
            "datatype": "coolingRate",
            "count": 1,
            "data": {"0": 0.999}
        }
        
        self.json_data["numberOfSteps"] = {
            "datatype": "numberOfSteps",
            "count": 1,
            "data": {"0": 10000}
        }
        
        self.json_data["ppmGroupSeparation"] = {
            "datatype": "ppmGroupSeparation",
            "count": 1,
            "data": {"0": 2}
        }
    
    def save_json(self, output_path: Union[str, Path]):
        """Save the JSON data to a file."""
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
        print(f"JSON data saved to: {output_path}")


if __name__ == "__main__":

    # check registration of user

    import uuid

    # MAC address-based (most persistent hardware ID)
    mac_based_id = hex(uuid.getnode())

    print(f"MAC-based ID: {mac_based_id}")

    json_obj = {"hostname": mac_based_id}

    entry_point = "https://test-simplenmr.pythonanywhere.com/check_machine_learning"

    # Make the POST request
    response = requests.post(
        entry_point,
        headers={'Content-Type': 'application/json'},
        json=json_obj
    )

    print(f"Response from server: {response.status_code} - {response.text}")

    if response.status_code == 200:
        # convert response.text to a dict based on it being valid json
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            print("Response is not valid JSON.")
            response_data = {}

        registered = response_data.get("status", False)

        # check if registered is of type str and equals "unregistered"
        if isinstance(registered, str) and registered.strip().lower() == "unregistered":
            print("Machine is unregistered. Redirecting to registration page.")
            registration_url = response_data["registration_url"]
            webbrowser.open(registration_url)

            proceed = False

        elif isinstance(registered, str) and registered.strip().lower() == "registered":

            proceed = True

        elif isinstance(registered, bool) and not registered:
            print("Something went wrong. Cannot determine registration status.")
            proceed = False

    else:
        print(f"Failed to check registration status: {response.status_code} - {response.text}")
        proceed = False


    if not proceed:
        print("Unable to register your machine. Please email support at simpleNMR@gmail.com for assistance.")
        sys.exit(1)





if proceed:
    print("Machine is registered. Proceeding with the application.")

    # Show dialog and get folder
    dialog = BrukerFolderDialog()
    if dialog.edit():
        bruker_data_dir = Path(dialog.bruker_folder)
        print(f"Selected Bruker folder: {bruker_data_dir}")

    else:
        print("No folder selected.")
        bruker_data_dir = None

    
    converter = BrukerToJSONConverter(bruker_data_dir)

    expts_with_peaks = []
    for expt_id, expt_data in converter.bruker_data.items():
        if expt_data.get('haspeaks', False):
            expts_with_peaks.append(expt_id)
            print(f"{expt_id} {expt_data['experimentType']} has peaks: {expt_data.get('haspeaks', False)}")

    expt_pdata_with_peaks = {}

    for expt_id in expts_with_peaks:
        expt_data = converter.bruker_data[expt_id]
        pdata = expt_data.get('pdata', {})
        pdata_with_peaks = []
        for pdata_key, pdata_val in pdata.items():
            if isinstance(pdata_val, dict) and 'peaklist' in pdata_val:
                peaklist = pdata_val['peaklist']
                if hasattr(peaklist, 'empty'):
                    if not peaklist.empty:
                        pdata_with_peaks.append(pdata_val.get('path', ''))
        if pdata_with_peaks:
            expt_pdata_with_peaks[expt_id] = pdata_with_peaks

    # Create and edit the instance

    # Usage:
    ProcessingClass = create_processing_class(expt_pdata_with_peaks, converter)
    param = ProcessingClass()
    result = param.edit()

    if result:
        param.view()


    if result:  # User clicked OK (not Cancel)
        print("User selections:")

        user_expt_selections = {}
        
        # Method 1: Access each attribute and convert index to actual choice
        for expt_id in expt_pdata_with_peaks.keys():
            expt_data = converter.bruker_data[expt_id]
            experiment_type = expt_data.get('experimentType', 'Unknown')
            if experiment_type == "Unknown":
                continue
                
            attr_name = f"expt_{expt_id}"
            if hasattr(param, attr_name):
                selected_index = getattr(param, attr_name)
                
                # Get the original choices from the stored ChoiceItem
                choice_item = ProcessingClass.expts[attr_name]
                choices = choice_item.get_prop("data", "choices")
                
                # Convert index to actual choice text
                if 0 <= selected_index < len(choices):
                    # choices is a list of tuples (value, label), we want the value
                    selected_choice = choices[selected_index][1]
                    print(f"{expt_id} ({experiment_type}): {selected_choice}")

                    if selected_choice != "SKIP":
                        user_expt_selections[expt_id] = {"experimentType": experiment_type, "procno": selected_choice}

    print("simulated_annealing:", param.simulated_annealing)
    print("ml_consent:", param.ml_consent)

    json_data = converter.convert_to_json( user_expt_selections=user_expt_selections, ml_consent=param.ml_consent, simulated_annealing=param.simulated_annealing)

    # temporary fix set hosname to one that is already registered
    # json_data["hostname"]["data"]["0"] = "Z49BR-HKPP041Y-42DHS-ANANTMPA"

    # Save to file
    output_file =   f"{converter.data_directory.name}_assignments.json"
    converter.save_json(output_file)



    # # Read the JSON file
    # with open('04164043_assignments.json', 'r') as f:
    #     json_data = json.load(f)

    # Make the POST request
    response = requests.post(
        'https://test-simplenmr.pythonanywhere.com/simpleMNOVA',
        headers={'Content-Type': 'application/json'},
        json=json_data
    )

    # Save response to file
    with open('test.html', 'w') as f:
        f.write(response.text)

    # Open in browser
    webbrowser.open('test.html')