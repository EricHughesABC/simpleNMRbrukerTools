import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, List
from dataclasses import dataclass, field
from datetime import datetime
import platform
import xml.etree.ElementTree as ET
import re

import numpy as np
import pandas as pd




def parse_bruker_2d_integral(file_content):
    """
    Parse Bruker 2D integral file content into a pandas DataFrame.
    
    Parameters:
    file_content (str): The content of the Bruker integral file as a string
    
    Returns:
    pd.DataFrame: Parsed integral data with columns for both F1 and F2 dimensions
    """
    
    lines = file_content.strip().split('\n')
    
    # Find the start of the data section (after the header)
    data_start = None
    for i, line in enumerate(lines):
        if '#' in line and 'SI_F1' in line:
            data_start = i
            break
    
    if data_start is None:
        raise ValueError("Could not find data section in file")
    
    # Parse the data
    data = []
    i = data_start + 1  # Start after header line
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # Check if this is an F1 data line (starts with integral number, followed by 1024)
        # F1 lines have 9 parts: num, SI, row1, row2, ppm1, ppm2, intensity, integral, mode
        parts = line.split()
        if len(parts) >= 9 and parts[0].isdigit() and parts[1] == '1024':
            try:
                integral_num = int(parts[0])
                f1_si = int(parts[1])
                f1_row1 = int(parts[2])
                f1_row2 = int(parts[3])
                f1_row1_ppm = float(parts[4])
                f1_row2_ppm = float(parts[5])
                abs_int = float(parts[6])
                integral = float(parts[7])
                mode = parts[8]
                
                # Parse F2 dimension line (next line)
                i += 1
                if i < len(lines):
                    f2_line = lines[i].strip()
                    f2_parts = f2_line.split()
                    # F2 lines have 5 parts: SI, col1, col2, ppm1, ppm2
                    if len(f2_parts) >= 5 and f2_parts[0] == '1024':
                        f2_si = int(f2_parts[0])
                        f2_col1 = int(f2_parts[1])
                        f2_col2 = int(f2_parts[2])
                        f2_col1_ppm = float(f2_parts[3])
                        f2_col2_ppm = float(f2_parts[4])
                        
                        # Add to data
                        data.append({
                            'integral_num': integral_num,
                            'F1_SI': f1_si,
                            'F1_row1': f1_row1,
                            'F1_row2': f1_row2,
                            'F1_row1_ppm': f1_row1_ppm,
                            'F1_row2_ppm': f1_row2_ppm,
                            'F2_SI': f2_si,
                            'F2_col1': f2_col1,
                            'F2_col2': f2_col2,
                            'F2_col1_ppm': f2_col1_ppm,
                            'F2_col2_ppm': f2_col2_ppm,
                            'abs_intensity': abs_int,
                            'integral': integral,
                            'mode': mode
                        })
                    else:
                        # If F2 line parsing fails, go back one step
                        i -= 1
            except (ValueError, IndexError):
                # If parsing fails, continue to next line
                pass
        
        i += 1
    
    # Create DataFrame
    df = pd.DataFrame(data)

    # create f1_ppm and f2_ppm columns by taking the average of the row/col ppm values
    df['f1_ppm'] = (df['F1_row1_ppm'] + df['F1_row2_ppm']) / 2
    df['f2_ppm'] = (df['F2_col1_ppm'] + df['F2_col2_ppm']) / 2

    # Reorder columns based on f1_ppm in descending order and reset index
    df = df.sort_values(by='f2_ppm', ascending=False).reset_index(drop=True)
    
    return df


def xml_to_dataframe(xml_content, peak_type='Peak2D'):
    # Parse the XML
    root = ET.fromstring(xml_content)
    
    # Find all Peak2D elements
    peaks = root.findall(f'.//{peak_type}')
    
    # Extract data from each peak
    data = []

    if peak_type == 'Peak2D':
        # For 2D peaks, extract F1 and F2 coordinates, annotation, intensity, and type
        for peak in peaks:
            data.append({
                'f1_ppm': float(peak.get('F1')),
                'f2_ppm': float(peak.get('F2')),
                'annotation': peak.get('annotation', ''),
                'intensity': float(peak.get('intensity')),
                'type': int(peak.get('type'))
            })
    elif peak_type == 'Peak1D':
      for peak in peaks:
          data.append({
              'ppm': float(peak.get('F1')),
              'intensity': float(peak.get('intensity')),
              'type': int(peak.get('type')),
              'annotation': peak.get('annotation', ''),
          })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    #  sort by f2_ppm if it exists or by ppm in descending order reset index
    if 'f2_ppm' in df.columns:
        df.sort_values(by='f2_ppm', ascending=False, inplace=True)
    else:
        df.sort_values(by='ppm', ascending=False, inplace=True) 
    return df





class BrukerParameterFile:
    """Parse Bruker parameter files (acqus, procs, etc.) with dictionary-like access."""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.parameters = {}
        self.raw_content = ""
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Parameter file not found: {file_path}")
        
        self._parse_file()
    
    def _parse_file(self):
        """Parse the parameter file and extract all parameters."""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.raw_content = f.read()
        
        lines = self.raw_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('$$') or line.startswith('##END') or not line:
                i += 1
                continue
            
            if line.startswith('##$'):
                param_name, value, i = self._parse_parameter(lines, i)
                if param_name:
                    self.parameters[param_name] = value
            else:
                i += 1
    
    def _parse_parameter(self, lines, start_index):
        """Parse a single parameter that may span multiple lines."""
        line = lines[start_index].strip()
        
        match = re.match(r'##\$([^=]+)=\s*(.*)', line)
        if not match:
            return None, None, start_index + 1
        
        param_name = match.group(1)
        value_str = match.group(2)
        
        # Check if this is an array parameter
        if '(' in param_name and ')' in param_name:
            array_match = re.match(r'([^(]+)\s*\((\d+)\.\.(\d+)\)', param_name)
            if array_match:
                base_name = array_match.group(1)
                array_values, next_index = self._parse_array_values(lines, start_index, value_str)
                return base_name, array_values, next_index
        
        # Single value parameter
        parsed_value = self._convert_value(value_str)
        return param_name, parsed_value, start_index + 1
    
    def _parse_array_values(self, lines, start_index, initial_value):
        """Parse array values that may span multiple lines."""
        values = []
        current_line = initial_value
        i = start_index
        
        while i < len(lines):
            line_values = current_line.strip().split()
            values.extend(line_values)
            
            i += 1
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith('##'):
                    break
                elif not next_line:
                    continue
                else:
                    current_line = next_line
            else:
                break
        
        converted_values = [self._convert_value(v) for v in values]
        return converted_values, i
    
    def _convert_value(self, value_str):
        """Convert string value to appropriate Python type."""
        value_str = value_str.strip()
        
        if not value_str:
            return ""
        
        if value_str.startswith('<') and value_str.endswith('>'):
            return value_str[1:-1]
        
        if value_str.lower() in ['yes', 'no']:
            return value_str.lower() == 'yes'
        
        try:
            if '.' not in value_str and 'e' not in value_str.lower():
                return int(value_str)
            else:
                return float(value_str)
        except ValueError:
            return value_str
    
    def get(self, key, default=None):
        return self.parameters.get(key, default)
    
    def __getitem__(self, key):
        return self.parameters[key]
    
    def __contains__(self, key):
        return key in self.parameters
    
    def keys(self):
        return self.parameters.keys()

experiments = {'HSQC': {'pulseprogram': [ "hsqcedetgpsisp2.3.ptg",
                                          "hsqcedetgpsisp2.3",
                                         "gHSQCAD", 
                                         "hsqcedetgpsp.3",
                                         "gHSQC",
                                         "inv4gp.wu",
                                         "hsqcetgp",
                                         "gns_noah3-BSScc.eeh",
                                         "hsqcedetgpsisp2.4"
                                        ], 
                        'nuclei': ['1H', '13C'], 
                        'dimensions': 2},

                'HMBC': {'pulseprogram': [ "ghmbc.wu", 
                                           "gHMBC", 
                                           "hmbcetgpl3nd", 
                                           "hmbcetgpl3nd.ptg",
                                           "gHMBCAD",
                                           "hmbcgpndqf",
                                           "gns_noah3-BSScc.eeh",
                                           "shmbcctetgpl2nd"
                                        ],
                          'nuclei': ['1H', '13C'], 
                          'dimensions': 2},

                'COSY': {'pulseprogram': [ "cosygpqf", 
                                           "cosygp", 
                                           "gcosy", 
                                           "cosygpmfppqf", 
                                           "cosygpmfqf", 
                                           "gCOSY",
                                           "cosygpppqf_ptype",
                                           "cosyqf45",
                                           "cosygpmfphpp",
                                           "cosygpppqf_ptype.jaa"
                                          ],    
                          'nuclei': ['1H', '1H'], 
                          'dimensions': 2
                        },

   
                'NOESY': {'pulseprogram': ['noesygpphppzs', ],
                        'nuclei': ['1H', '1H'], 
                        'dimensions': 2},

                'C13_1D': {'pulseprogram': ["zgdc30", 
                                            "s2pul", 
                                            "zgpg30",
                                            "zgzrse", 
                                            "zg0dc.fr" 
                                            ],
                           'nuclei': ['13C',], 
                           'dimensions': 1},

                'H1_1D': {'pulseprogram': ["zg30",  
                                     "s2pul", 
                                     "zg", 
                                     "zgcppr"],
                        'nuclei': ['1H',], 
                        'dimensions': 1},

                'PURESHIFT_1D': {'pulseprogram': ["ja_PSYCHE_pr_03b", 
                                              "reset_psychetse.ptg" ],
                                 'nuclei': ['1H',], 
                                 'dimensions': 2},

                'HSQC_CLIPCOSY': {'pulseprogram': ["hsqc_clip_cosy_mc_notation.eeh",
                                                   "gns_noah3-BSScc.eeh"],
                                    'nuclei': ['1H', '13C'], 
                                    'dimensions': 2},

                'DDEPT_CH3_ONLY': {'pulseprogram': ['hcdeptedetgpzf'],
                                   'nuclei': ['1H', '13C'], 
                                   'dimensions': 2},
                                   
                'DEPT135': {'pulseprogram': ["dept135.wu", 
                                             "DEPT", 
                                             "deptsp135"],
                            'nuclei': ['13C'],
                            'dimensions': 1},
}


class BrukerDataDirectory:
    """    A class to represent a directory containing Bruker NMR data files.
    It scans the directory for Bruker folders, which are identified by the presence of 'acqu*' files.
    """
    def __init__(self, path: Union[str, Path], experiments):
        self.path = Path(path)

        self._all_bruker_folders = self.find_bruker_folders(self.path)

        self.add_pulseprogram()
        self.add_nuclei()
        self.identify_experiment_types(experiments)

        self.find_peaklist_files()

        self.find_2D_integral_files()


    def find_2D_integral_files(self):

        # find the 2D integrals in the Bruker data directory
        for expt_id, expt_data in self.items():
            if expt_data["dimensions"] != 2:
                continue
            for proc_dir in expt_data["pdata"]["procfolders"]:
                procno = proc_dir.name
                integral_file = proc_dir / "int2d"
                if not integral_file.exists():
                    print(f"No integral file found for {expt_id} in {procno}")
                    continue
                with open(integral_file, 'r', encoding='utf-8') as f:
                    integral_content = f.read()
                    try:
                        integral_df = parse_bruker_2d_integral(integral_content)
                        expt_data["pdata"][procno]["integrals"] = integral_df
                        if integral_df.empty:
                            expt_data["hasIntegrals"] = False
                            expt_data["pdata"][procno]["hasIntegrals"] = False
                        else:
                            expt_data["hasIntegrals"] = True
                            expt_data["pdata"][procno]["hasIntegrals"] = True
                        print(f"Parsed integrals for {expt_id} in {procno}:")
                    except:
                        print(f"Failed to parse integrals for {expt_id} in {procno}")
                        continue


    def find_peaklist_files(self):
        """
        We are looking for the peaklist.xml files in the processed data diretories.
        We also need to know pass the dimensions of the  xml read function as either a 1 or 2 to represent 1D or 2D data.
        """
        for expt_id, expt_data in self.items():
            # pdata = expt_data.get('pdata', {})
            # if pdata:
            #     for 
  
            peak_type = 'Peak2D' if expt_data['dimensions'] == 2 else 'Peak1D'
            expt_type = expt_data.get("experimentType", "Unknown")

            if expt_type == "PURESHIFT_1D":
                peak_type = 'Peak1D'
            for proc_dir in expt_data["pdata"]["procfolders"]:
                peaklist_file = proc_dir / 'peaklist.xml'
                if peaklist_file.exists():
                    with open(peaklist_file, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                        print(expt_id, expt_type, len(xml_content))
                    peak_df = xml_to_dataframe(xml_content, peak_type=peak_type)

                    expt_data["peaklist"] = peak_df
                    expt_data["pdata"][proc_dir.name]["peaklist"] = peak_df

                    # if the peaklist is empty set "haspeaks" to False
                    if peak_df.empty:
                        expt_data["haspeaks"] = False
                        expt_data["pdata"][proc_dir.name]["haspeaks"] = False
                    else:
                        expt_data["haspeaks"] = True
                        expt_data["pdata"][proc_dir.name]["haspeaks"] = True

    def find_bruker_folders(self, path):
        """        
        Scans the directory for Bruker folders, which are identified by the presence of 'acqu*' files.
        """
        # is a lict of dictionaries, each
        all_bruker_folders = {}

        # Find all folders in the directory
        for p in path.glob('*'):
            if p.is_dir():

                self._read_acqu_files(p, all_bruker_folders)
                all_bruker_folders[p.name]['pdata'] = self._find_pdata(p)
                self._find_proc_files(all_bruker_folders[p.name]['pdata'])

                # # read proc* files in pdata folders
                # self._read_proc_files(all_bruker_folders[p.name]['pdata'])

        return all_bruker_folders

    def _read_acqu_files(self, p, all_bruker_folders):
        """
        Process a single folder to check if it is a Bruker folder and extract acqu* info.
        """
        acq_files = [sub_p for sub_p in p.glob('acqu*')]
        if acq_files:
            all_bruker_folders[p.name] = {
                'path': p,
                'acq_files': acq_files,
                'dimensions': len(acq_files)//2,
            }
            for acq_file in acq_files:
                try:
                    acqu = BrukerParameterFile(acq_file)
                    all_bruker_folders[p.name][acq_file.name] = acqu
                except Exception as e:
                    print(f"Error reading {acq_file}: {e}")
        else:
            print(f"No Bruker acqu files found in: {p.name}")
            all_bruker_folders[p.name] = {
                'path': p,
                'acq_files': [],
                'dimensions': 0
            }

    

    def _find_proc_files(self, pdata_dict):
        """
        For each processed data folder in pdata_dict['procfolders'], find proc* files and
        add them to pdata_dict using the folder name as key.
        """
        for pdata_folder in pdata_dict['procfolders']:
            proc_files = [pf for pf in pdata_folder.glob('proc*')]
            if proc_files:
                pdata_dict[pdata_folder.name] = {
                    'path': pdata_folder,
                    'proc_files': proc_files
                }
                for proc_file in proc_files:
                    try:
                        pdata_dict[pdata_folder.name][proc_file.name] = BrukerParameterFile(proc_file)
                    except Exception as e:
                        print(f"Error reading {proc_file}: {e}")
            else:
                pdata_dict[pdata_folder.name] = {
                    'path': pdata_folder,
                    'proc_files': []
                }

    def _find_pdata(self, experiment_path):
        """
        Finds processed data directories (pdata) within a Bruker experiment directory.
        Returns a dictionary with 'path' and 'procfolders' keys.
        """
        pdata_dir = experiment_path / 'pdata'
        if pdata_dir.is_dir():
            pdata_folders = [pf for pf in pdata_dir.glob('*') if pf.is_dir() and pf.name.isdigit()]
            if pdata_folders:
                return {'path': pdata_dir, 'procfolders': pdata_folders}
        else:
            return {'path': pdata_dir, 'procfolders': []}
        
    def _read_proc_files(self, pdata_dict):
        """
        Reads all proc* files in each processed data folder and returns a dictionary
        mapping folder names to BrukerParameterFile objects for each proc file.
        """
        proc_data = {}
        for pdata_folder in pdata_dict['procfolders']:
            proc_files = [pf for pf in pdata_folder.glob('proc*')]
            # print the name of the proc_files found
            proc_data[pdata_folder.name] = {}
            for proc_file in proc_files:
                try:
                    proc_data[pdata_folder.name][proc_file.name] = BrukerParameterFile(proc_file)
                except Exception as e:
                    print(f"Error reading {proc_file}: {e}")
        return proc_data
    
    def add_pulseprogram(self):
        """
        Adds the pulseprogram information to each experiment in the directory.
        """
        for expt in self._all_bruker_folders.keys():
            if 'acqu' not in self._all_bruker_folders[expt].keys():
                self._all_bruker_folders[expt]['pulseprogram'] = 'Unknown'
            else:
                self._all_bruker_folders[expt]['pulseprogram'] = self._all_bruker_folders[expt]['acqu'].get('PULPROG', 'Unknown')

    def add_nuclei(self):
        """
        Adds nuclei information to each experiment in the directory based on its dimension.
        """
        for expt_id, expt_data in self._all_bruker_folders.items():
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


    def identify_experiment_types(self, experiments: Dict[str, Dict[str, Any]]) -> None:
        """
        Identifies the type of NMR experiment for each experiment in the directory.
        Returns a dictionary mapping experiment ID to experiment type (or None if not matched).
        """
        experiment_types = {}
        for expt_id, expt_data in self._all_bruker_folders.items():
            matched = False
            for exp_type, exp_info in experiments.items():
                if (expt_data['pulseprogram'] in exp_info['pulseprogram'] and
                    set(expt_data['nuclei']) == set(exp_info['nuclei']) and
                    expt_data['dimensions'] == exp_info['dimensions']):
                    print(f"Experiment {expt_id} matches {exp_type}")
                    expt_data["experimentType"] = exp_type
                    matched = True
                    break
            if not matched:
                print(f"Experiment {expt_id}, {expt_data['pulseprogram']} does not match any known experiment type.")
                expt_data["experimentType"] = "Unknown"


    def __str__(self):
        lll = list(self._all_bruker_folders.keys())
        lll_int = sorted([int(l) for l in lll if l.isdigit()])
        lll_rest = sorted([l for l in lll if not l.isdigit()])
        return str([*map(str, lll_int), *lll_rest])
    

    
    def experiment(self, expt_id):
        """
        Returns the experiment data for a given experiment ID.
        """
        if expt_id in self._all_bruker_folders:
            return self._all_bruker_folders[expt_id]
        else:
            raise ValueError(f"Experiment ID {expt_id} not found in the directory.")
        
    def __getitem__(self, expt_id):
        """
        Allows access to the experiment data using the square bracket notation.
        """
        return self._all_bruker_folders[expt_id]
    
    def get(self, expt_id, default=None):
        """
        Returns the experiment data for a given experiment ID, or a default value if not found.
        """
        return self._all_bruker_folders.get(expt_id, default)

    def __iter__(self):
        return iter(self._all_bruker_folders.values())
    
    def items(self):
        """
        Returns an iterator over the items in the directory.
        Each item is a tuple of (experiment ID, experiment data).
        """
        return self._all_bruker_folders.items()
    def keys(self):
        """
        Returns the keys of the directory, which are the experiment IDs.
        """
        return self._all_bruker_folders.keys()
    def values(self):
        """
        Returns the values of the directory, which are the experiment data.
        """
        return self._all_bruker_folders.values()



