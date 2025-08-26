"""
bruker_nmr/src/parsers/integral_parser.py
"""
import pandas as pd
from typing import List, Dict, Any


def parse_bruker_2d_integral(file_content: str) -> pd.DataFrame:
    """
    Parse Bruker 2D integral file content into a pandas DataFrame.
    
    Args:
        file_content: The content of the Bruker integral file as a string
        
    Returns:
        DataFrame with parsed integral data
    """
    lines = file_content.strip().split('\n')
    data_start = _find_data_start(lines)
    
    if data_start is None:
        raise ValueError("Could not find data section in file")
    
    data = _parse_integral_data(lines, data_start)
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Add center point calculations
        df['f1_ppm'] = (df['F1_row1_ppm'] + df['F1_row2_ppm']) / 2
        df['f2_ppm'] = (df['F2_col1_ppm'] + df['F2_col2_ppm']) / 2
        
        # Sort by f2_ppm descending
        df = df.sort_values(by='f2_ppm', ascending=False).reset_index(drop=True)
    
    return df


def _find_data_start(lines: List[str]) -> int:
    """Find the start of the data section."""
    for i, line in enumerate(lines):
        if '#' in line and 'SI_F1' in line:
            return i
    return None


def _parse_integral_data(lines: List[str], start_index: int) -> List[Dict[str, Any]]:
    """Parse the integral data from lines."""
    data = []
    i = start_index + 1
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Parse F1 line
        f1_data = _parse_f1_line(line)
        if f1_data:
            # Parse F2 line (next line)
            i += 1
            if i < len(lines):
                f2_data = _parse_f2_line(lines[i].strip())
                if f2_data:
                    integral_entry = {**f1_data, **f2_data}
                    # Add center points
                    integral_entry['f1_ppm'] = (f1_data['F1_row1_ppm'] + f1_data['F1_row2_ppm']) / 2
                    integral_entry['f2_ppm'] = (f2_data['F2_col1_ppm'] + f2_data['F2_col2_ppm']) / 2
                    data.append(integral_entry)
                else:
                    i -= 1
        
        i += 1
    
    return data


def _parse_f1_line(line: str) -> Dict[str, Any]:
    """Parse F1 dimension line."""
    parts = line.split()
    if len(parts) >= 9 and parts[0].isdigit() and parts[1] == '1024':
        try:
            return {
                'integral_num': int(parts[0]),
                'F1_SI': int(parts[1]),
                'F1_row1': int(parts[2]),
                'F1_row2': int(parts[3]),
                'F1_row1_ppm': float(parts[4]),
                'F1_row2_ppm': float(parts[5]),
                'abs_intensity': float(parts[6]),
                'integral': float(parts[7]),
                'mode': parts[8]
            }
        except (ValueError, IndexError):
            return None
    return None


def _parse_f2_line(line: str) -> Dict[str, Any]:
    """Parse F2 dimension line."""
    parts = line.split()
    if len(parts) >= 5 and parts[0] == '1024':
        try:
            return {
                'F2_SI': int(parts[0]),
                'F2_col1': int(parts[1]),
                'F2_col2': int(parts[2]),
                'F2_col1_ppm': float(parts[3]),
                'F2_col2_ppm': float(parts[4])
            }
        except (ValueError, IndexError):
            return None
    return None