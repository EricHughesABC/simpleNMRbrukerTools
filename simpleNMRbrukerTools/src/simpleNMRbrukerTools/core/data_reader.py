"""
bruker_nmr/src/core/data_reader.py
"""
from pathlib import Path
from typing import Dict, List, Union, Any
from ..parsers.parameter_parser import BrukerParameterFile
from ..parsers.peak_parser import parse_peak_xml
from ..parsers.integral_parser import parse_bruker_2d_integral


class BrukerDataDirectory:
    """
    A class to represent a directory containing Bruker NMR data files.
    
    Attributes:
        path (Path): Path to the data directory
        experiments (Dict): Dictionary of experiment configurations
        data (Dict): Parsed experiment data
    """
    
    def __init__(self, path: Union[str, Path], experiment_configs: Dict[str, Dict]):
        """
        Initialize Bruker data directory reader.
        
        Args:
            path: Path to directory containing Bruker data
            experiment_configs: Dictionary defining experiment types and parameters
        """
        self.path = Path(path)
        self.experiment_configs = experiment_configs
        self.data = {}
        
        self._scan_directory()
        self._identify_experiments()
        self._process_peaks_and_integrals()
    
    def _scan_directory(self) -> None:
        """Scan directory for Bruker experiment folders."""
        for folder in self.path.glob('*'):
            if folder.is_dir():
                acqu_files = list(folder.glob('acqu*'))
                if acqu_files:
                    self._process_experiment_folder(folder, acqu_files)
    
    def _process_experiment_folder(self, folder: Path, acqu_files: List[Path]) -> None:
        """Process a single experiment folder."""
        expt_id = folder.name
        
        self.data[expt_id] = {
            'path': folder,
            'dimensions': len(acqu_files) // 2,
            'acqu_files': acqu_files
        }
        
        # Parse acquisition files
        for acqu_file in acqu_files:
            try:
                self.data[expt_id][acqu_file.name] = BrukerParameterFile(acqu_file)
            except Exception as e:
                print(f"Error reading {acqu_file}: {e}")
        
        # Add pulse program and nuclei info
        self._add_experiment_metadata(expt_id)
        
        # Find and process pdata
        self._process_pdata(expt_id, folder)
    
    def _add_experiment_metadata(self, expt_id: str) -> None:
        """Add pulse program and nuclei information."""
        expt_data = self.data[expt_id]
        
        # Pulse program
        if 'acqu' in expt_data:
            expt_data['pulseprogram'] = expt_data['acqu'].get('PULPROG', 'Unknown')
        else:
            expt_data['pulseprogram'] = 'Unknown'
        
        # Nuclei
        if 'acqu' in expt_data:
            acqu = expt_data['acqu']
            acqu2 = expt_data.get('acqu2', {})
            
            if expt_data['dimensions'] == 1:
                expt_data['nuclei'] = [acqu.get('NUC1', 'Unknown')]
            elif expt_data['dimensions'] == 2:
                expt_data['nuclei'] = [acqu.get('NUC1', 'Unknown'), acqu2.get('NUC1', 'Unknown')]
            else:
                expt_data['nuclei'] = ['Unknown']
        else:
            expt_data['nuclei'] = ['Unknown']
    
    def _process_pdata(self, expt_id: str, folder: Path) -> None:
        """Process processed data directories."""
        pdata_dir = folder / 'pdata'
        if not pdata_dir.is_dir():
            self.data[expt_id]['pdata'] = {'procfolders': []}
            return
        
        proc_folders = [f for f in pdata_dir.glob('*') if f.is_dir() and f.name.isdigit()]
        self.data[expt_id]['pdata'] = {
            'path': pdata_dir,
            'procfolders': proc_folders
        }
        
        # Process each proc folder
        for proc_folder in proc_folders:
            self._process_proc_folder(expt_id, proc_folder)
    
    def _process_proc_folder(self, expt_id: str, proc_folder: Path) -> None:
        """Process a single processed data folder."""
        proc_data = {
            'path': proc_folder,
            'proc_files': list(proc_folder.glob('proc*'))
        }
        
        # Parse proc files
        for proc_file in proc_data['proc_files']:
            try:
                proc_data[proc_file.name] = BrukerParameterFile(proc_file)
            except Exception as e:
                print(f"Error reading {proc_file}: {e}")
        
        self.data[expt_id]['pdata'][proc_folder.name] = proc_data
    
    def _identify_experiments(self) -> None:
        """Identify experiment types based on configuration."""
        for expt_id, expt_data in self.data.items():
            matched = False
            
            for exp_type, exp_config in self.experiment_configs.items():
                if self._matches_experiment_config(expt_data, exp_config):
                    expt_data['experimentType'] = exp_type
                    matched = True
                    print(f"Experiment {expt_id} identified as {exp_type}")
                    break
            
            if not matched:
                expt_data['experimentType'] = 'Unknown'
                print(f"Experiment {expt_id} ({expt_data['pulseprogram']}) not recognized")
    
    def _matches_experiment_config(self, expt_data: Dict, config: Dict) -> bool:
        """Check if experiment matches configuration."""
        return (expt_data['pulseprogram'] in config['pulseprogram'] and
                set(expt_data['nuclei']) == set(config['nuclei']) and
                expt_data['dimensions'] == config['dimensions'])
    
    def _process_peaks_and_integrals(self) -> None:
        """Process peak lists and integrals for all experiments."""
        for expt_id, expt_data in self.data.items():
            self._process_experiment_peaks(expt_id, expt_data)
            if expt_data['dimensions'] == 2:
                self._process_experiment_integrals(expt_id, expt_data)
    
    def _process_experiment_peaks(self, expt_id: str, expt_data: Dict) -> None:
        """Process peak lists for an experiment."""
        peak_type = self._get_peak_type(expt_data)
        
        for proc_folder in expt_data['pdata']['procfolders']:
            peaklist_file = proc_folder / 'peaklist.xml'
            if peaklist_file.exists():
                try:
                    with open(peaklist_file, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    
                    peak_df = parse_peak_xml(xml_content, peak_type)
                    
                    # Store peak data
                    expt_data['peaklist'] = peak_df
                    expt_data['pdata'][proc_folder.name]['peaklist'] = peak_df
                    
                    # Set has_peaks flag
                    has_peaks = not peak_df.empty
                    expt_data['haspeaks'] = has_peaks
                    expt_data['pdata'][proc_folder.name]['haspeaks'] = has_peaks
                    
                except Exception as e:
                    print(f"Error processing peaks for {expt_id}: {e}")
    
    def _get_peak_type(self, expt_data: Dict) -> str:
        """Determine peak type based on experiment data."""
        if expt_data.get('experimentType') == 'PURESHIFT_1D':
            return 'Peak1D'
        return 'Peak2D' if expt_data['dimensions'] == 2 else 'Peak1D'
    
    def _process_experiment_integrals(self, expt_id: str, expt_data: Dict) -> None:
        """Process 2D integrals for an experiment."""
        for proc_folder in expt_data['pdata']['procfolders']:
            integral_file = proc_folder / 'int2d'
            if integral_file.exists():
                try:
                    with open(integral_file, 'r', encoding='utf-8') as f:
                        integral_content = f.read()
                    
                    integral_df = parse_bruker_2d_integral(integral_content)
                    
                    # Store integral data
                    expt_data['pdata'][proc_folder.name]['integrals'] = integral_df
                    
                    # Set has_integrals flag
                    has_integrals = not integral_df.empty
                    expt_data['hasIntegrals'] = has_integrals
                    expt_data['pdata'][proc_folder.name]['hasIntegrals'] = has_integrals
                    
                except Exception as e:
                    print(f"Error processing integrals for {expt_id}: {e}")
    
    # Dictionary-like interface
    def get(self, expt_id: str, default: Any = None) -> Any:
        """Get experiment data with default."""
        return self.data.get(expt_id, default)
    
    def __getitem__(self, expt_id: str) -> Any:
        """Get experiment data."""
        return self.data[expt_id]
    
    def __contains__(self, expt_id: str) -> bool:
        """Check if experiment exists."""
        return expt_id in self.data
    
    def keys(self):
        """Get experiment IDs."""
        return self.data.keys()
    
    def values(self):
        """Get experiment data values."""
        return self.data.values()
    
    def items(self):
        """Get experiment items."""
        return self.data.items()
    
if __name__ == "__main__":
    pass