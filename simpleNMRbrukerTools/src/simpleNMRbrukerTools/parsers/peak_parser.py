"""
bruker_nmr/src/parsers/peak_parser.py
"""
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Literal


def parse_peak_xml(xml_content: str, peak_type: Literal['Peak1D', 'Peak2D'] = 'Peak2D') -> pd.DataFrame:
    """
    Parse Bruker peak XML file to DataFrame.
    
    Args:
        xml_content: XML content as string
        peak_type: Type of peaks to parse ('Peak1D' or 'Peak2D')
        
    Returns:
        DataFrame with peak data
    """
    root = ET.fromstring(xml_content)
    peaks = root.findall(f'.//{peak_type}')
    
    if peak_type == 'Peak2D':
        data = [
            {
                'f1_ppm': float(peak.get('F1')),
                'f2_ppm': float(peak.get('F2')),
                'annotation': peak.get('annotation', ''),
                'intensity': float(peak.get('intensity')),
                'type': int(peak.get('type'))
            }
            for peak in peaks
        ]
        sort_col = 'f2_ppm'
    else:  # Peak1D
        data = [
            {
                'ppm': float(peak.get('F1')),
                'intensity': float(peak.get('intensity')),
                'type': int(peak.get('type')),
                'annotation': peak.get('annotation', ''),
            }
            for peak in peaks
        ]
        sort_col = 'ppm'
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
    
    return df