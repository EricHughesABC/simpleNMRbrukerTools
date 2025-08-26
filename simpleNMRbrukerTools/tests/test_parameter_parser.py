"""
tests/test_parameter_parser.py
"""
import pytest
import tempfile
from pathlib import Path
from bruker_nmr.src.core.parameter_parser import BrukerParameterFile


class TestBrukerParameterFile:
    
    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            BrukerParameterFile("nonexistent_file.txt")
    
    def test_simple_parameter_parsing(self):
        """Test parsing of simple parameters."""
        content = """##$PULPROG= <zg30>
##$TD= 65536
##$NS= 16
##$SWH= 10000.000
##$FIDRES= 0.152588"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            f.flush()
            
            parser = BrukerParameterFile(f.name)
            
            assert parser.get('PULPROG') == 'zg30'
            assert parser.get('TD') == 65536
            assert parser.get('NS') == 16
            assert parser.get('SWH') == 10000.0
            assert parser.get('FIDRES') == 0.152588
            
        Path(f.name).unlink()  # cleanup
    
    def test_array_parameter_parsing(self):
        """Test parsing of array parameters."""
        content = """##$O1P(0..7)= 0 0 0 0 0 0 0 0
##$PLW(0..63)= 13.5 0 0 0"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            f.flush()
            
            parser = BrukerParameterFile(f.name)
            
            assert parser.get('O1P') == [0, 0, 0, 0, 0, 0, 0, 0]
            assert parser.get('PLW') == [13.5, 0, 0, 0]
            
        Path(f.name).unlink()
    
    def test_boolean_parameter_parsing(self):
        """Test parsing of boolean parameters."""
        content = """##$DIGMOD= yes
##$GRPDLY= no"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            f.flush()
            
            parser = BrukerParameterFile(f.name)
            
            assert parser.get('DIGMOD') is True
            assert parser.get('GRPDLY') is False
            
        Path(f.name).unlink()
    
    def test_dictionary_interface(self):
        """Test dictionary-like interface."""
        content = """##$PULPROG= <zg30>
##$TD= 65536"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            f.flush()
            
            parser = BrukerParameterFile(f.name)
            
            assert 'PULPROG' in parser
            assert 'NONEXISTENT' not in parser
            assert parser['TD'] == 65536
            assert 'PULPROG' in parser.keys()
            
        Path(f.name).unlink()


"""
tests/test_peak_parser.py
"""
import pytest
import pandas as pd
from bruker_nmr.src.parsers.peak_parser import parse_peak_xml


class TestPeakParser:
    
    def test_parse_2d_peaks(self):
        """Test parsing of 2D peak XML."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
    <Peak2D F1="7.5" F2="125.3" intensity="1000.0" type="0" annotation=""/>
    <Peak2D F1="6.8" F2="110.5" intensity="800.0" type="1" annotation="CH"/>
</PeakList>"""
        
        df = parse_peak_xml(xml_content, 'Peak2D')
        
        assert len(df) == 2
        assert df.iloc[0]['f1_ppm'] == 7.5
        assert df.iloc[0]['f2_ppm'] == 125.3
        assert df.iloc[0]['intensity'] == 1000.0
        assert df.iloc[1]['annotation'] == 'CH'
        
        # Check sorting (should be sorted by f2_ppm descending)
        assert df.iloc[0]['f2_ppm'] > df.iloc[1]['f2_ppm']
    
    def test_parse_1d_peaks(self):
        """Test parsing of 1D peak XML."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
    <Peak1D F1="7.5" intensity="1000.0" type="0" annotation=""/>
    <Peak1D F1="6.8" intensity="800.0" type="1" annotation="CH3"/>
</PeakList>"""
        
        df = parse_peak_xml(xml_content, 'Peak1D')
        
        assert len(df) == 2
        assert df.iloc[0]['ppm'] == 7.5
        assert df.iloc[0]['intensity'] == 1000.0
        assert df.iloc[1]['annotation'] == 'CH3'
        
        # Check sorting (should be sorted by ppm descending)
        assert df.iloc[0]['ppm'] > df.iloc[1]['ppm']
    
    def test_empty_peak_list(self):
        """Test handling of empty peak lists."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
</PeakList>"""
        
        df = parse_peak_xml(xml_content, 'Peak2D')
        assert df.empty


"""
tests/test_integral_parser.py
"""
import pytest
import pandas as pd
from bruker_nmr.src.parsers.integral_parser import parse_bruker_2d_integral


class TestIntegralParser:
    
    def test_parse_2d_integrals(self):
        """Test parsing of 2D integral file."""
        content = """# 2D integral file
# SI_F1 data
0 1024 100 200 7.5 6.5 1000.0 500.0 mode1
1024 50 150 125.3 110.5
1 1024 300 400 8.2 7.8 1200.0 600.0 mode2
1024 75 175 140.2 130.1"""
        
        df = parse_bruker_2d_integral(content)
        
        assert len(df) == 2
        
        # Check first integral
        assert df.iloc[0]['integral_num'] == 0
        assert df.iloc[0]['F1_row1_ppm'] == 7.5
        assert df.iloc[0]['F1_row2_ppm'] == 6.5
        assert df.iloc[0]['F2_col1_ppm'] == 125.3
        assert df.iloc[0]['F2_col2_ppm'] == 110.5
        assert df.iloc[0]['integral'] == 500.0
        assert df.iloc[0]['f1_ppm'] == 7.0  # Average of 7.5 and 6.5
        assert df.iloc[0]['f2_ppm'] == 117.9  # Average of 125.3 and 110.5
    
    def test_invalid_integral_file(self):
        """Test handling of invalid integral file."""
        content = """Invalid content without proper format"""
        
        with pytest.raises(ValueError, match="Could not find data section"):
            parse_bruker_2d_integral(content)


"""
tests/test_data_reader.py
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from bruker_nmr.src.core.data_reader import BrukerDataDirectory
from bruker_nmr.src.config import EXPERIMENT_CONFIGS


class TestBrukerDataDirectory:
    
    @pytest.fixture
    def mock_data_directory(self):
        """Create a mock Bruker data directory structure."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create experiment folder
        exp_folder = temp_dir / "1"
        exp_folder.mkdir()
        
        # Create acqu file
        acqu_file = exp_folder / "acqu"
        acqu_content = """##$PULPROG= <zg30>
##$NUC1= <1H>
##$TD= 65536"""
        acqu_file.write_text(acqu_content)
        
        # Create pdata structure
        pdata_dir = exp_folder / "pdata" / "1"
        pdata_dir.mkdir(parents=True)
        
        # Create proc file
        proc_file = pdata_dir / "procs"
        proc_content = """##$SI= 32768
##$SF= 400.13"""
        proc_file.write_text(proc_content)
        
        # Create peak list
        peak_file = pdata_dir / "peaklist.xml"
        peak_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
    <Peak1D F1="7.5" intensity="1000.0" type="0" annotation=""/>
</PeakList>"""
        peak_file.write_text(peak_content)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_directory_scanning(self, mock_data_directory):
        """Test scanning of Bruker data directory."""
        reader = BrukerDataDirectory(mock_data_directory, EXPERIMENT_CONFIGS)
        
        assert "1" in reader.data
        assert reader.data["1"]["dimensions"] == 1
        assert reader.data["1"]["pulseprogram"] == "zg30"
        assert reader.data["1"]["nuclei"] == ["1H"]
        assert reader.data["1"]["experimentType"] == "H1_1D"
    
    def test_peak_processing(self, mock_data_directory):
        """Test peak processing."""
        reader = BrukerDataDirectory(mock_data_directory, EXPERIMENT_CONFIGS)
        
        assert reader.data["1"]["haspeaks"] is True
        assert len(reader.data["1"]["peaklist"]) == 1
        assert reader.data["1"]["peaklist"].iloc[0]["ppm"] == 7.5
    
    def test_dictionary_interface(self, mock_data_directory):
        """Test dictionary-like interface."""
        reader = BrukerDataDirectory(mock_data_directory, EXPERIMENT_CONFIGS)
        
        assert "1" in reader
        assert reader["1"]["pulseprogram"] == "zg30"
        assert reader.get("1")["experimentType"] == "H1_1D"
        assert reader.get("nonexistent") is None


"""
tests/test_json_converter.py
"""
import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path
from bruker_nmr.src.core.json_converter import BrukerToJSONConverter


class TestJSONConverter:
    
    @pytest.fixture
    def mock_bruker_data(self):
        """Create mock Bruker data for testing."""
        mock_data = Mock()
        mock_data.data = {
            "1": {
                "experimentType": "H1_1D",
                "dimensions": 1,
                "nuclei": ["1H"],
                "pulseprogram": "zg30",
                "path": Path("/mock/path/1"),
                "haspeaks": True,
                "peaklist": Mock(),
                "pdata": {
                    "1": {
                        "peaklist": Mock(),
                        "haspeaks": True
                    }
                },
                "acqu": Mock()
            }
        }
        mock_data.items.return_value = mock_data.data.items()
        mock_data.get.side_effect = lambda key, default=None: mock_data.data.get(key, default)
        
        return mock_data
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_json_conversion(self, mock_bruker_class, mock_bruker_data):
        """Test basic JSON conversion."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter("/mock/path")
        
        user_selections = {
            "1": {"experimentType": "H1_1D", "procno": "1"}
        }
        
        json_data = converter.convert_to_json(
            user_selections, 
            ml_consent=True, 
            simulated_annealing=False
        )
        
        # Check basic structure
        assert "hostname" in json_data
        assert "workingDirectory" in json_data
        assert "ml_consent" in json_data
        assert "simulatedAnnealing" in json_data
        
        # Check ML consent
        assert json_data["ml_consent"]["data"]["0"] is True
        
        # Check simulated annealing
        assert json_data["simulatedAnnealing"]["data"]["0"] is False


"""
tests/test_integration.py
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from bruker_nmr.src.core.data_reader import BrukerDataDirectory
from bruker_nmr.src.core.json_converter import BrukerToJSONConverter
from bruker_nmr.src.config import EXPERIMENT_CONFIGS


class TestIntegration:
    
    @pytest.fixture
    def full_mock_directory(self):
        """Create a comprehensive mock directory for integration testing."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create 1H experiment
        h1_folder = temp_dir / "10"
        h1_folder.mkdir()
        
        # 1H acqu file
        h1_acqu = h1_folder / "acqu"
        h1_acqu_content = """##$PULPROG= <zg30>
##$NUC1= <1H>
##$TD= 65536
##$BF1= 400.13"""
        h1_acqu.write_text(h1_acqu_content)
        
        # 1H pdata
        h1_pdata = h1_folder / "pdata" / "1"
        h1_pdata.mkdir(parents=True)
        
        h1_proc = h1_pdata / "procs"
        h1_proc_content = """##$SI= 32768
##$SF= 400.13"""
        h1_proc.write_text(h1_proc_content)
        
        h1_peaks = h1_pdata / "peaklist.xml"
        h1_peak_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
    <Peak1D F1="7.26" intensity="1000.0" type="0" annotation="CHCl3"/>
    <Peak1D F1="2.50" intensity="800.0" type="1" annotation="DMSO"/>
</PeakList>"""
        h1_peaks.write_text(h1_peak_content)
        
        # Create HSQC experiment
        hsqc_folder = temp_dir / "20"
        hsqc_folder.mkdir()
        
        # HSQC acqu files
        hsqc_acqu = hsqc_folder / "acqu"
        hsqc_acqu_content = """##$PULPROG= <hsqcedetgpsisp2.3>
##$NUC1= <1H>
##$TD= 2048
##$BF1= 400.13"""
        hsqc_acqu.write_text(hsqc_acqu_content)
        
        hsqc_acqu2 = hsqc_folder / "acqu2"
        hsqc_acqu2_content = """##$NUC1= <13C>
##$TD= 512
##$BF1= 100.61"""
        hsqc_acqu2.write_text(hsqc_acqu2_content)
        
        # HSQC pdata
        hsqc_pdata = hsqc_folder / "pdata" / "1"
        hsqc_pdata.mkdir(parents=True)
        
        hsqc_proc = hsqc_pdata / "procs"
        hsqc_proc.write_text("##$SI= 2048")
        
        hsqc_proc2 = hsqc_pdata / "proc2s"
        hsqc_proc2.write_text("##$SI= 1024")
        
        hsqc_peaks = hsqc_pdata / "peaklist.xml"
        hsqc_peak_content = """<?xml version="1.0" encoding="UTF-8"?>
<PeakList>
    <Peak2D F1="7.26" F2="77.2" intensity="1000.0" type="0" annotation=""/>
    <Peak2D F1="2.50" F2="39.5" intensity="800.0" type="1" annotation=""/>
</PeakList>"""
        hsqc_peaks.write_text(hsqc_peak_content)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_full_workflow(self, full_mock_directory):
        """Test complete workflow from directory scan to JSON output."""
        # Read data
        reader = BrukerDataDirectory(full_mock_directory, EXPERIMENT_CONFIGS)
        
        # Verify data reading
        assert "10" in reader.data
        assert "20" in reader.data
        assert reader.data["10"]["experimentType"] == "H1_1D"
        assert reader.data["20"]["experimentType"] == "HSQC"
        
        # Verify peak processing
        assert reader.data["10"]["haspeaks"] is True
        assert reader.data["20"]["haspeaks"] is True
        assert len(reader.data["10"]["peaklist"]) == 2
        assert len(reader.data["20"]["peaklist"]) == 2
        
        # Convert to JSON
        converter = BrukerToJSONConverter(full_mock_directory)
        
        user_selections = {
            "10": {"experimentType": "H1_1D", "procno": "1"},
            "20": {"experimentType": "HSQC", "procno": "1"}
        }
        
        json_data = converter.convert_to_json(
            user_selections,
            ml_consent=False,
            simulated_annealing=True
        )
        
        # Verify JSON structure
        assert "hostname" in json_data
        assert "chosenSpectra" in json_data
        assert "H1_1D_0" in json_data
        assert "HSQC_0" in json_data
        
        # Verify spectrum data
        h1_spectrum = json_data["H1_1D_0"]
        assert h1_spectrum["type"] == "1D"
        assert h1_spectrum["nucleus"] == "1H"
        assert h1_spectrum["peaks"]["count"] == 2
        
        hsqc_spectrum = json_data["HSQC_0"]
        assert hsqc_spectrum["type"] == "2D"
        assert hsqc_spectrum["subtype"] == "13C1H, HSQC-EDITED"
        assert hsqc_spectrum["peaks"]["count"] == 2


"""
tests/conftest.py
"""
import pytest
import sys
from pathlib import Path

# Add src directory to Python path for testing
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))





