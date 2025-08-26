"""
bruker_nmr/src/core/json_converter.py

Complete BrukerToJSONConverter implementation - simplified and documented.
"""
import json
import uuid
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Optional RDKit import
try:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from .data_reader import BrukerDataDirectory
from ..config import EXPERIMENT_CONFIGS


class BrukerToJSONConverter:
    """
    Converts Bruker NMR data to JSON format similar to MNova output.
    
    This class handles the conversion of Bruker NMR data structures into a JSON format
    that's compatible with MNova's expected input structure. It includes support for
    molecular structure processing using RDKit when available.
    
    Attributes:
        data_directory (Path): Path to the Bruker data directory
        smiles (str): SMILES string for the molecule
        molfile_content (str): Content of the mol file
        bruker_data (BrukerDataDirectory): Parsed Bruker data
        json_data (Dict): Output JSON structure
        rdkit_mol: RDKit molecule object (if available)
    """
    
    def __init__(self, data_directory: Union[str, Path], smiles: str = None, molfile_content: str = None):
        """
        Initialize the converter.
        
        Args:
            data_directory: Path to directory containing Bruker data
            smiles: Optional SMILES string for the molecule
            molfile_content: Optional mol file content as string
        """
        self.data_directory = Path(data_directory)
        self.smiles = smiles
        self.molfile_content = molfile_content
        
        # Molecular structure attributes
        self.mol_files = []
        self.selected_mol_file = None
        self.rdkit_mol = None
        
        # Initialize the Bruker data reader
        self.bruker_data = BrukerDataDirectory(data_directory, EXPERIMENT_CONFIGS)
        
        # Initialize the JSON structure
        self.json_data = {}
        
        # Process mol file if available and RDKit is installed
        if RDKIT_AVAILABLE:
            self._process_mol_files()

        if self.rdkit_mol:
            self.num_atoms = self.rdkit_mol.GetNumAtoms()
            self.num_carbons = sum(1 for atom in self.rdkit_mol.GetAtoms() if atom.GetSymbol() == 'C')
            self.num_CH3_groups = sum(1 for atom in self.rdkit_mol.GetAtoms() if atom.GetSymbol() == 'C' and atom.GetTotalNumHs() == 3)
            self.num_CH2_groups = sum(1 for atom in self.rdkit_mol.GetAtoms() if atom.GetSymbol() == 'C' and atom.GetTotalNumHs() == 2)
            self.num_CH1_groups = sum(1 for atom in self.rdkit_mol.GetAtoms() if atom.GetSymbol() == 'C' and atom.GetTotalNumHs() == 1)
            self.num_CH0_groups = sum(1 for atom in self.rdkit_mol.GetAtoms() if atom.GetSymbol() == 'C' and atom.GetTotalNumHs() == 0)
            for atom in self.rdkit_mol.GetAtoms():
                if atom.GetSymbol() == 'C':
                    print(atom.GetTotalNumHs())
                    catom = atom

            
            print("dir(catom)")
            print(dir(catom))
        else:
            self.num_atoms = 0
            self.num_carbons = 0
            self.num_CH3_groups = -1
            self.num_CH2_groups = -1
            self.num_CH1_groups = -1
            self.num_CH0_groups = -1

        print(f"Initialized BrukerToJSONConverter with {self.num_atoms} atoms, {self.num_carbons} carbons")
        print(f"CH3 groups: {self.num_CH3_groups}, CH2 groups: {self.num_CH2_groups}, CH1 groups: {self.num_CH1_groups}, CH0 groups: {self.num_CH0_groups}")

    def find_mol_files(self) -> List[Path]:
        """
        Find all .mol files in the directory.
        
        Returns:
            List of Path objects for found mol files
        """
        self.mol_files = list(self.data_directory.glob("*.mol"))
        print(f"Found {len(self.mol_files)} mol file(s): {[f.name for f in self.mol_files]}")
        return self.mol_files
    
    def select_mol_file(self, index: int = 0) -> Optional[Path]:
        """
        Select a mol file to use.
        
        Args:
            index: Index of mol file to select (default: 0 for first file)
            
        Returns:
            Path to selected mol file or None if no files found
        """
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
        """
        Load the selected mol file using RDKit.
        
        Returns:
            True if successful, False otherwise
        """
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
        """
        Generate SMILES string from the loaded RDKit molecule.
        
        Returns:
            SMILES string or empty string if not available
        """
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
    
    def _process_mol_files(self) -> None:
        """Process mol files in the directory."""
        if not RDKIT_AVAILABLE:
            return
            
        self.find_mol_files()
        if self.select_mol_file():
            if self.load_mol_file():
                self.generate_smiles_from_mol()
    
    def convert_to_json(self, user_expt_selections: Dict[str, Dict], 
                       ml_consent: bool = False, 
                       simulated_annealing: bool = False) -> Dict[str, Any]:
        """
        Main method to convert Bruker data to JSON format.
        
        Args:
            user_expt_selections: Dictionary mapping experiment IDs to their settings
            ml_consent: Whether user consents to ML data usage
            simulated_annealing: Whether to use simulated annealing
            
        Returns:
            Complete JSON data structure
        """
        # Clear any existing data
        self.json_data = {}
        
        # Add basic molecular information
        self._add_molecular_info()
        
        # Add system information
        self._add_system_info()
        
        # Add atom information
        self._add_atom_info()
        
        # Add NMR spectra data
        self._add_nmr_spectra(user_expt_selections)
        
        # Add experiment settings
        self._add_experiment_settings()
        
        # Add processing parameters
        self._add_processing_parameters()
        
        # Add user preferences
        self._add_ml_consent(ml_consent)
        self._add_simulated_annealing(simulated_annealing)
        
        return self.json_data
    
    def _add_molecular_info(self) -> None:
        """Add SMILES and molfile information to JSON."""
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
    
    def _add_system_info(self) -> None:
        """Add system and hostname information."""
        # Generate hardware-based ID
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
            "data": {"0": str(self.data_directory.absolute()).replace("\\", "/")}
        }
        
        self.json_data["workingFilename"] = {
            "datatype": "workingFilename",
            "count": 1,
            "data": {"0": self.data_directory.name}
        }
    
    def _add_atom_info(self) -> None:
        """Add atom information from mol file or placeholders."""
        if RDKIT_AVAILABLE and self.rdkit_mol:
            # Use RDKit molecule to create atom info
            self.json_data["allAtomsInfo"] = self._create_all_atoms_info_from_mol()
            self.json_data["carbonAtomsInfo"] = self._create_carbon_atoms_info_from_mol()
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
        
        # Placeholder for NMR assignments and predictions
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
    
    def _create_all_atoms_info_from_mol(self) -> Dict[str, Any]:
        """
        Create the allAtomsInfo structure from the RDKit molecule.
        
        Returns:
            Dictionary containing all atom information
        """
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
                "numProtons": atom.GetTotalNumHs()
            }
            all_atoms_data["data"][str(atom_idx)] = atom_info
        
        return all_atoms_data
    
    def _create_carbon_atoms_info_from_mol(self) -> Dict[str, Any]:
        """
        Create the carbonAtomsInfo structure from the RDKit molecule.
        
        Returns:
            Dictionary containing carbon atom information
        """
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
                    "numProtons": atom.GetTotalNumHs()
                }
                carbon_atoms_data["data"][str(atom_idx)] = atom_info
                carbon_count += 1
        
        carbon_atoms_data["count"] = carbon_count
        return carbon_atoms_data
    
    def _add_nmr_spectra(self, user_expt_selections: Dict[str, Dict]) -> None:
        """
        Convert Bruker NMR spectra to JSON format.
        
        Args:
            user_expt_selections: Dictionary mapping experiment IDs to their settings
        """
        chosen_spectra = []
        spectrum_counter = 0
        experiment_identifiers = []
        
        for expt_id, expt_selection_values in user_expt_selections.items():
            exp_type = expt_selection_values.get("experimentType", "Unknown")
            procno = expt_selection_values["procno"]
            
            if exp_type == "Unknown":
                continue
            
            print(f"Processing experiment {expt_id} with type {exp_type}")
            
            expt_data = self.bruker_data.get(expt_id, {})
            if not expt_data:
                print(f"Warning: No data found for experiment {expt_id}")
                continue
            
            pulseprogram = expt_data.get("pulseprogram", "unknown")
            nuclei = expt_data.get("nuclei", ["Unknown"])
            dimensions = expt_data.get("dimensions", 1)
            
            # Create spectrum identifier
            exp_type_count = experiment_identifiers.count(exp_type)
            experiment_identifiers.append(exp_type)
            spectrum_id = f"{exp_type}_{exp_type_count}"
            
            # Create spectrum entry
            spectrum_data = self._create_spectrum_entry(expt_data, spectrum_id, procno)
            
            # Add to main JSON data
            self.json_data[spectrum_id] = spectrum_data
            
            # Add to chosen spectra list
            if dimensions == 1:
                nucleus_str = nuclei[0] if nuclei else "Unknown"
            else:
                nucleus_str = f"[{', '.join(nuclei)}]"
            
            chosen_entry = f"{nucleus_str} {dimensions}D {pulseprogram} {spectrum_id} {exp_type}"
            chosen_spectra.append(chosen_entry)
            
            spectrum_counter += 1
        
        # Add chosen spectra to JSON
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
    
    def _create_spectrum_entry(self, expt_data: Dict[str, Any], spectrum_id: str, procno: str) -> Dict[str, Any]:
        """
        Create a spectrum entry in the JSON format.
        
        Args:
            expt_data: Experiment data dictionary
            spectrum_id: Unique identifier for the spectrum
            procno: Processing number
            
        Returns:
            Dictionary containing spectrum data
        """
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
            "temperature": self._get_temperature(acqu)
        }
        
        # Add peaks from peaklist if available
        peaks_data = self._get_peaks_data(expt_data, procno, dimensions)
        spectrum_entry["peaks"] = peaks_data
        
        # Add integrals for 2D experiments
        if dimensions == 2:
            integrals_data = self._get_integrals_data(expt_data, procno)
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

    def _get_temperature(self, acqu: Dict[str, Any]) -> str:
        """Extract temperature from acquisition parameters."""
        if hasattr(acqu, 'get'):
            temperature = acqu.get("TE", "Unknown")
            if isinstance(temperature, (int, float)):
                return f"{temperature}"
            elif isinstance(temperature, list) and len(temperature) > 0:
                return str(temperature[0])
            return str(temperature)
        return "Unknown"
    
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
    
    def _get_probe_info(self, acqu: Dict[str, Any]) -> str:
        """Extract probe information from acquisition parameters."""
        if hasattr(acqu, 'get'):
            probhd = acqu.get("PROBHD", "Unknown probe")
        else:
            probhd = "Unknown probe"
        return str(probhd)
    
    def _get_spec_frequency(self, acqu: Dict[str, Any], acqu2: Dict[str, Any], dimensions: int) -> Union[float, str]:
        """Get spectrometer frequency."""
        if dimensions == 1:
            if hasattr(acqu, 'get'):
                return acqu.get("BF1", 0.0)
            return 0.0
        else:
            bf1 = acqu.get("BF1", 0.0) if hasattr(acqu, 'get') else 0.0
            bf2 = acqu2.get("BF1", 0.0) if (acqu2 and hasattr(acqu2, 'get')) else 0.0
            return f"[{bf2}, {bf1}]"
    
    def _get_peaks_data(self, expt_data: Dict[str, Any], procno: str, dimensions: int) -> Dict[str, Any]:
        """Get peaks data from experiment."""
        pdata = expt_data.get("pdata", {})
        proc_data = pdata.get(procno, {})
        
        if "peaklist" in proc_data and hasattr(proc_data["peaklist"], 'empty'):
            if not proc_data["peaklist"].empty:
                return self._convert_peaklist_to_json(proc_data["peaklist"], dimensions)
        
        # Return empty peaks structure
        return {"datatype": "peaks", "data": {}, "count": 0}
    
    def _get_integrals_data(self, expt_data: Dict[str, Any], procno: str) -> Dict[str, Any]:
        """Get integrals data for 2D experiments."""
        pdata = expt_data.get("pdata", {})
        proc_data = pdata.get(procno, {})
        
        if "integrals" in proc_data and hasattr(proc_data["integrals"], 'empty'):
            if not proc_data["integrals"].empty:
                return self._convert_2d_integrals_to_json(proc_data["integrals"])
        
        # Return empty integrals structure
        return {"datatype": "integrals", "count": 0, "normValue": 1, "data": {}}
    
    def _convert_peaklist_to_json(self, peaklist_df, dimensions: int) -> Dict[str, Any]:
        """Convert pandas DataFrame peaklist to JSON format."""
        peaks_data = {"datatype": "peaks", "data": {}, "count": len(peaklist_df)}
        
        for idx, row in peaklist_df.iterrows():
            peak_entry = {
                "intensity": float(row.get("intensity", 0.0)),
                # "type": int(row.get("type", 0)),
                "type": 0,
                "annotation": str(row.get("annotation", ""))
            }
            
            if dimensions == 1:
                peak_entry["delta1"] = float(row.get("ppm", 0.0))
                peak_entry["delta2"] = 0
            else:
                peak_entry["delta1"] = float(row.get("f1_ppm", 0.0))
                peak_entry["delta2"] = float(row.get("f2_ppm", 0.0))
            
            peaks_data["data"][str(idx)] = peak_entry
        
        return peaks_data
    
    def _convert_2d_integrals_to_json(self, integrals_df) -> Dict[str, Any]:
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
                "delta1": float(row.get("f1_ppm", 0.0)),          # F1 center
                "delta2": float(row.get("f2_ppm", 0.0)),          # F2 center
                "type": 0
            }
            
            integrals_data["data"][str(idx)] = integral_entry
        
        return integrals_data
    
    def _add_experiment_settings(self) -> None:
        """Add experiment-specific settings."""
        # Add spectra with peaks
        spectra_with_peaks = []
        for expt_id, expt_data in self.bruker_data.items():
            if expt_data.get('haspeaks', False):
                nuclei = expt_data.get("nuclei", ["Unknown"])
                dimensions = expt_data.get("dimensions", 1)
                pulseprogram = expt_data.get("pulseprogram", "unknown")
                exp_type = expt_data.get("experimentType", "Unknown")
                
                if dimensions == 1:
                    nucleus_str = f"{nuclei[0]} 1D"
                else:
                    nucleus_str = f"[{', '.join(nuclei)}] {exp_type}"
                
                spectrum_name = f"{nucleus_str} {pulseprogram} {expt_id}.{'fid' if dimensions == 1 else 'ser'}_0"
                spectra_with_peaks.append(spectrum_name)
        
        self.json_data["spectraWithPeaks"] = {
            "datatype": "spectraWithPeaks",
            "count": len(spectra_with_peaks),
            "data": {str(i): spec for i, spec in enumerate(spectra_with_peaks)}
        }
    
    def _add_processing_parameters(self) -> None:
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
        
        # Default simulated annealing parameters
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
    
    def _add_ml_consent(self, ml_consent: bool) -> None:
        """Add ML consent information."""
        self.json_data["ml_consent"] = {
            "datatype": "ml_consent",
            "count": 1,
            "data": {"0": ml_consent}
        }
    
    def _add_simulated_annealing(self, simulated_annealing: bool) -> None:
        """Add simulated annealing information."""
        self.json_data["simulatedAnnealing"] = {
            "datatype": "simulatedAnnealing",
            "count": 1,
            "data": {"0": simulated_annealing}
        }
    
    def save_json(self, output_path: Union[str, Path]) -> None:
        """
        Save the JSON data to a file.
        
        Args:
            output_path: Path where to save the JSON file
        """
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
        print(f"JSON data saved to: {output_path}")
    
    def get_json_string(self, indent: int = 4) -> str:
        """
        Get the JSON data as a formatted string.
        
        Args:
            indent: Number of spaces for indentation
            
        Returns:
            JSON string
        """
        return json.dumps(self.json_data, indent=indent, ensure_ascii=False)


# Example usage and testing function
def main():
    """Example usage of the BrukerToJSONConverter."""
    import sys
    from pathlib import Path
    
    if len(sys.argv) != 2:
        print("Usage: python json_converter.py <bruker_data_directory>")
        return
    
    data_dir = Path(sys.argv[1])
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        return
    
    # Create converter
    converter = BrukerToJSONConverter(data_dir)
    
    # Example user selections (you would get these from GUI)
    user_selections = {}
    
    # Find experiments with peaks
    for expt_id, expt_data in converter.bruker_data.items():
        if expt_data.get('haspeaks', False):
            exp_type = expt_data.get('experimentType', 'Unknown')
            if exp_type != 'Unknown':
                # Use first available processed data folder
                pdata = expt_data.get('pdata', {})
                proc_folders = pdata.get('procfolders', [])
                if proc_folders:
                    procno = proc_folders[0].name
                    user_selections[expt_id] = {
                        'experimentType': exp_type,
                        'procno': procno
                    }
                    print(f"Added experiment {expt_id} ({exp_type}) with procno {procno}")
    
    if not user_selections:
        print("No experiments with peaks found.")
        return
    
    # Convert to JSON
    json_data = converter.convert_to_json(
        user_selections,
        ml_consent=False,
        simulated_annealing=True
    )
    
    # Save to file
    output_file = data_dir.name + "_assignments.json"
    converter.save_json(output_file)
    
    print(f"Conversion complete. Output saved to: {output_file}")
    print(f"Processed {len(user_selections)} experiments")


if __name__ == "__main__":
    main()