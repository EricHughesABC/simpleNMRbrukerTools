"""
tests/test_json_converter.py

Complete test suite for BrukerToJSONConverter
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the class we're testing
from bruker_nmr.src.core.json_converter import BrukerToJSONConverter


class TestBrukerToJSONConverter:
    """Test cases for BrukerToJSONConverter class."""
    
    @pytest.fixture
    def mock_bruker_data(self):
        """Create mock Bruker data for testing."""
        mock_data = Mock()
        mock_data.data = {
            "10": {
                "experimentType": "H1_1D",
                "dimensions": 1,
                "nuclei": ["1H"],
                "pulseprogram": "zg30",
                "path": Path("/mock/path/10"),
                "haspeaks": True,
                "peaklist": Mock(),
                "pdata": {
                    "1": {
                        "peaklist": Mock(),
                        "haspeaks": True,
                        "path": Path("/mock/path/10/pdata/1")
                    }
                },
                "acqu": Mock()
            },
            "20": {
                "experimentType": "HSQC",
                "dimensions": 2,
                "nuclei": ["1H", "13C"],
                "pulseprogram": "hsqcedetgpsisp2.3",
                "path": Path("/mock/path/20"),
                "haspeaks": True,
                "peaklist": Mock(),
                "pdata": {
                    "1": {
                        "peaklist": Mock(),
                        "haspeaks": True,
                        "integrals": Mock(),
                        "hasIntegrals": True,
                        "path": Path("/mock/path/20/pdata/1")
                    }
                },
                "acqu": Mock(),
                "acqu2": Mock()
            }
        }
        
        # Configure mock methods
        mock_data.items.return_value = mock_data.data.items()
        mock_data.get.side_effect = lambda key, default=None: mock_data.data.get(key, default)
        mock_data.__contains__ = lambda self, key: key in mock_data.data
        mock_data.__getitem__ = lambda self, key: mock_data.data[key]
        
        # Configure acquisition parameter mocks
        mock_data.data["10"]["acqu"].get.side_effect = lambda key, default=None: {
            "PROBHD": "5 mm PABBO BB/",
            "BF1": 400.13
        }.get(key, default)
        
        mock_data.data["20"]["acqu"].get.side_effect = lambda key, default=None: {
            "PROBHD": "5 mm PABBO BB/",
            "BF1": 400.13
        }.get(key, default)
        
        mock_data.data["20"]["acqu2"].get.side_effect = lambda key, default=None: {
            "BF1": 100.61
        }.get(key, default)
        
        return mock_data
    
    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_peaklist_1d(self):
        """Create mock 1D peaklist DataFrame."""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=2)
        mock_df.iterrows.return_value = [
            (0, {"ppm": 7.26, "intensity": 1000.0, "type": 0, "annotation": "CHCl3"}),
            (1, {"ppm": 2.50, "intensity": 800.0, "type": 1, "annotation": "DMSO"})
        ]
        return mock_df
    
    @pytest.fixture
    def mock_peaklist_2d(self):
        """Create mock 2D peaklist DataFrame."""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=2)
        mock_df.iterrows.return_value = [
            (0, {"f1_ppm": 7.26, "f2_ppm": 77.2, "intensity": 1000.0, "type": 0, "annotation": ""}),
            (1, {"f1_ppm": 2.50, "f2_ppm": 39.5, "intensity": 800.0, "type": 1, "annotation": ""})
        ]
        return mock_df
    
    @pytest.fixture
    def mock_integrals_2d(self):
        """Create mock 2D integrals DataFrame."""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=1)
        mock_df.iterrows.return_value = [
            (0, {
                "integral": 1000.0,
                "F1_row1_ppm": 7.5,
                "F1_row2_ppm": 7.0,
                "F2_col1_ppm": 80.0,
                "F2_col2_ppm": 75.0,
                "f1_ppm": 7.25,
                "f2_ppm": 77.5
            })
        ]
        return mock_df
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_initialization(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test converter initialization."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        
        assert converter.data_directory == temp_directory
        assert converter.smiles is None
        assert converter.molfile_content is None
        assert converter.json_data == {}
        mock_bruker_class.assert_called_once()
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_initialization_with_smiles(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test converter initialization with SMILES."""
        mock_bruker_class.return_value = mock_bruker_data
        
        smiles = "CCO"
        converter = BrukerToJSONConverter(temp_directory, smiles=smiles)
        
        assert converter.smiles == smiles
    
    def test_find_mol_files(self, temp_directory):
        """Test finding mol files in directory."""
        # Create test mol files
        mol_file1 = temp_directory / "compound1.mol"
        mol_file2 = temp_directory / "compound2.mol"
        mol_file1.touch()
        mol_file2.touch()
        
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            found_files = converter.find_mol_files()
        
        assert len(found_files) == 2
        assert mol_file1 in found_files
        assert mol_file2 in found_files
    
    def test_select_mol_file(self, temp_directory):
        """Test selecting a mol file."""
        # Create test mol file
        mol_file = temp_directory / "compound.mol"
        mol_file.touch()
        
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            converter.mol_files = [mol_file]
            selected = converter.select_mol_file()
        
        assert selected == mol_file
        assert converter.selected_mol_file == mol_file
    
    def test_select_mol_file_no_files(self, temp_directory):
        """Test selecting mol file when none exist."""
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            selected = converter.select_mol_file()
        
        assert selected is None
        assert converter.selected_mol_file is None
    
    @patch('bruker_nmr.src.core.json_converter.RDKIT_AVAILABLE', True)
    @patch('bruker_nmr.src.core.json_converter.Chem')
    def test_load_mol_file_success(self, mock_chem, temp_directory):
        """Test successful mol file loading."""
        # Create test mol file with content
        mol_file = temp_directory / "compound.mol"
        mol_content = """
  Mrv2014 01012021

  3  2  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
M  END
"""
        mol_file.write_text(mol_content)
        
        # Mock RDKit molecule
        mock_mol = Mock()
        mock_mol.GetNumAtoms.return_value = 3
        mock_chem.MolFromMolFile.return_value = mock_mol
        
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            converter.selected_mol_file = mol_file
            result = converter.load_mol_file()
        
        assert result is True
        assert converter.molfile_content == mol_content
        assert converter.rdkit_mol == mock_mol
        mock_chem.MolFromMolFile.assert_called_once_with(str(mol_file))
    
    @patch('bruker_nmr.src.core.json_converter.RDKIT_AVAILABLE', False)
    def test_load_mol_file_rdkit_unavailable(self, temp_directory):
        """Test mol file loading when RDKit is unavailable."""
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            result = converter.load_mol_file()
        
        assert result is False
    
    @patch('bruker_nmr.src.core.json_converter.RDKIT_AVAILABLE', True)
    @patch('bruker_nmr.src.core.json_converter.Chem')
    def test_generate_smiles_from_mol(self, mock_chem, temp_directory):
        """Test SMILES generation from mol file."""
        mock_mol = Mock()
        mock_chem.MolToSmiles.return_value = "CCO"
        
        with patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory'):
            converter = BrukerToJSONConverter(temp_directory)
            converter.rdkit_mol = mock_mol
            result = converter.generate_smiles_from_mol()
        
        assert result == "CCO"
        assert converter.smiles == "CCO"
        mock_chem.MolToSmiles.assert_called_once_with(mock_mol)
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_convert_to_json_basic(self, mock_bruker_class, mock_bruker_data, 
                                  mock_peaklist_1d, mock_peaklist_2d, temp_directory):
        """Test basic JSON conversion."""
        mock_bruker_class.return_value = mock_bruker_data
        
        # Configure peaklist mocks
        mock_bruker_data.data["10"]["pdata"]["1"]["peaklist"] = mock_peaklist_1d
        mock_bruker_data.data["20"]["pdata"]["1"]["peaklist"] = mock_peaklist_2d
        
        converter = BrukerToJSONConverter(temp_directory)
        
        user_selections = {
            "10": {"experimentType": "H1_1D", "procno": "1"},
            "20": {"experimentType": "HSQC", "procno": "1"}
        }
        
        json_data = converter.convert_to_json(
            user_selections,
            ml_consent=True,
            simulated_annealing=False
        )
        
        # Check basic structure
        assert "hostname" in json_data
        assert "workingDirectory" in json_data
        assert "workingFilename" in json_data
        assert "chosenSpectra" in json_data
        assert "ml_consent" in json_data
        assert "simulatedAnnealing" in json_data
        
        # Check experiment spectra
        assert "H1_1D_0" in json_data
        assert "HSQC_0" in json_data
        
        # Check ML consent
        assert json_data["ml_consent"]["data"]["0"] is True
        
        # Check simulated annealing
        assert json_data["simulatedAnnealing"]["data"]["0"] is False
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_molecular_info_addition(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test molecular information addition to JSON."""
        mock_bruker_class.return_value = mock_bruker_data
        
        smiles = "CCO"
        molfile_content = "mock mol file content"
        
        converter = BrukerToJSONConverter(temp_directory, smiles=smiles, molfile_content=molfile_content)
        converter._add_molecular_info()
        
        assert "smiles" in converter.json_data
        assert converter.json_data["smiles"]["data"]["0"] == smiles
        
        assert "molfile" in converter.json_data
        assert converter.json_data["molfile"]["data"]["0"] == molfile_content
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_system_info_addition(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test system information addition to JSON."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter._add_system_info()
        
        assert "hostname" in converter.json_data
        assert "workingDirectory" in converter.json_data
        assert "workingFilename" in converter.json_data
        
        # Check working directory format
        working_dir = converter.json_data["workingDirectory"]["data"]["0"]
        assert "/" in working_dir  # Should use forward slashes
        
        # Check working filename
        working_filename = converter.json_data["workingFilename"]["data"]["0"]
        assert working_filename == temp_directory.name
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    @patch('bruker_nmr.src.core.json_converter.RDKIT_AVAILABLE', True)
    def test_atom_info_with_rdkit(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test atom information addition with RDKit."""
        mock_bruker_class.return_value = mock_bruker_data
        
        # Mock RDKit molecule
        mock_mol = Mock()
        mock_atoms = [Mock(), Mock(), Mock()]  # 3 atoms
        mock_atoms[0].GetSymbol.return_value = "C"
        mock_atoms[0].GetTotalNumHs.return_value = 3
        mock_atoms[1].GetSymbol.return_value = "C"
        mock_atoms[1].GetTotalNumHs.return_value = 2
        mock_atoms[2].GetSymbol.return_value = "O"
        mock_atoms[2].GetTotalNumHs.return_value = 1
        
        mock_mol.GetNumAtoms.return_value = 3
        mock_mol.GetAtoms.return_value = mock_atoms
        
        converter = BrukerToJSONConverter(temp_directory)
        converter.rdkit_mol = mock_mol
        converter._add_atom_info()
        
        # Check all atoms info
        assert "allAtomsInfo" in converter.json_data
        assert converter.json_data["allAtomsInfo"]["count"] == 3
        assert len(converter.json_data["allAtomsInfo"]["data"]) == 3
        
        # Check carbon atoms info
        assert "carbonAtomsInfo" in converter.json_data
        assert converter.json_data["carbonAtomsInfo"]["count"] == 2  # 2 carbon atoms
        assert len(converter.json_data["carbonAtomsInfo"]["data"]) == 2
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    @patch('bruker_nmr.src.core.json_converter.RDKIT_AVAILABLE', False)
    def test_atom_info_without_rdkit(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test atom information addition without RDKit."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter._add_atom_info()
        
        # Check placeholder structures
        assert "allAtomsInfo" in converter.json_data
        assert converter.json_data["allAtomsInfo"]["count"] == 0
        assert converter.json_data["allAtomsInfo"]["data"] == {}
        
        assert "carbonAtomsInfo" in converter.json_data
        assert converter.json_data["carbonAtomsInfo"]["count"] == 0
        assert converter.json_data["carbonAtomsInfo"]["data"] == {}
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_convert_peaklist_1d(self, mock_bruker_class, mock_bruker_data, 
                                mock_peaklist_1d, temp_directory):
        """Test 1D peaklist conversion."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        peaks_data = converter._convert_peaklist_to_json(mock_peaklist_1d, 1)
        
        assert peaks_data["datatype"] == "peaks"
        assert peaks_data["count"] == 2
        assert len(peaks_data["data"]) == 2
        
        # Check first peak
        peak_0 = peaks_data["data"]["0"]
        assert peak_0["delta1"] == 7.26
        assert peak_0["delta2"] == 0
        assert peak_0["intensity"] == 1000.0
        assert peak_0["annotation"] == "CHCl3"
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_convert_peaklist_2d(self, mock_bruker_class, mock_bruker_data, 
                                mock_peaklist_2d, temp_directory):
        """Test 2D peaklist conversion."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        peaks_data = converter._convert_peaklist_to_json(mock_peaklist_2d, 2)
        
        assert peaks_data["datatype"] == "peaks"
        assert peaks_data["count"] == 2
        assert len(peaks_data["data"]) == 2
        
        # Check first peak
        peak_0 = peaks_data["data"]["0"]
        assert peak_0["delta1"] == 7.26
        assert peak_0["delta2"] == 77.2
        assert peak_0["intensity"] == 1000.0
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_convert_2d_integrals(self, mock_bruker_class, mock_bruker_data, 
                                 mock_integrals_2d, temp_directory):
        """Test 2D integrals conversion."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        integrals_data = converter._convert_2d_integrals_to_json(mock_integrals_2d)
        
        assert integrals_data["datatype"] == "integrals"
        assert integrals_data["count"] == 1
        assert len(integrals_data["data"]) == 1
        
        # Check integral data
        integral_0 = integrals_data["data"]["0"]
        assert integral_0["intensity"] == 1000.0
        assert integral_0["delta1"] == 7.25
        assert integral_0["delta2"] == 77.5
        assert integral_0["rangeMax1"] == 7.5
        assert integral_0["rangeMin1"] == 7.0
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_spectrum_subtype_generation(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test spectrum subtype string generation."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        
        # Test 1H spectrum
        subtype_1h = converter._get_spectrum_subtype(["1H"], "H1_1D")
        assert subtype_1h == "1H"
        
        # Test HSQC spectrum
        subtype_hsqc = converter._get_spectrum_subtype(["1H", "13C"], "HSQC")
        assert subtype_hsqc == "13C1H, HSQC-EDITED"
        
        # Test COSY spectrum
        subtype_cosy = converter._get_spectrum_subtype(["1H", "1H"], "COSY")
        assert subtype_cosy == "1H1H, COSY"
        
        # Test HMBC spectrum
        subtype_hmbc = converter._get_spectrum_subtype(["1H", "13C"], "HMBC")
        assert subtype_hmbc == "13C1H, HMBC"
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_save_json(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test JSON file saving."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter.json_data = {"test": "data"}
        
        output_file = temp_directory / "test_output.json"
        converter.save_json(output_file)
        
        # Check file was created and contains correct data
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == {"test": "data"}
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_get_json_string(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test JSON string generation."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter.json_data = {"test": "data"}
        
        json_string = converter.get_json_string()
        
        # Check it's valid JSON
        parsed_data = json.loads(json_string)
        assert parsed_data == {"test": "data"}
        
        # Check indentation
        assert "    " in json_string  # 4-space indentation
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_ml_consent_addition(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test ML consent information addition."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter._add_ml_consent(True)
        
        assert "ml_consent" in converter.json_data
        assert converter.json_data["ml_consent"]["data"]["0"] is True
        
        converter._add_ml_consent(False)
        assert converter.json_data["ml_consent"]["data"]["0"] is False
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_simulated_annealing_addition(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test simulated annealing information addition."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter._add_simulated_annealing(True)
        
        assert "simulatedAnnealing" in converter.json_data
        assert converter.json_data["simulatedAnnealing"]["data"]["0"] is True
        
        converter._add_simulated_annealing(False)
        assert converter.json_data["simulatedAnnealing"]["data"]["0"] is False
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_processing_parameters_addition(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test processing parameters addition."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        converter._add_processing_parameters()
        
        # Check key processing parameters are added
        assert "carbonCalcPositionsMethod" in converter.json_data
        assert "MNOVAcalcMethod" in converter.json_data
        assert "randomizeStart" in converter.json_data
        assert "startingTemperature" in converter.json_data
        assert "endingTemperature" in converter.json_data
        assert "coolingRate" in converter.json_data
        assert "numberOfSteps" in converter.json_data
        assert "ppmGroupSeparation" in converter.json_data
        
        # Check default values
        assert converter.json_data["startingTemperature"]["data"]["0"] == 1000
        assert converter.json_data["endingTemperature"]["data"]["0"] == 0.1
        assert converter.json_data["coolingRate"]["data"]["0"] == 0.999
        assert converter.json_data["numberOfSteps"]["data"]["0"] == 10000
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_empty_user_selections(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test handling of empty user selections."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        
        json_data = converter.convert_to_json(
            {},  # Empty selections
            ml_consent=False,
            simulated_annealing=False
        )
        
        # Should still have basic structure
        assert "hostname" in json_data
        assert "chosenSpectra" in json_data
        assert json_data["chosenSpectra"]["count"] == 0
        assert json_data["chosenSpectra"]["data"] == {}
    
    @patch('bruker_nmr.src.core.json_converter.BrukerDataDirectory')
    def test_unknown_experiment_type_handling(self, mock_bruker_class, mock_bruker_data, temp_directory):
        """Test handling of unknown experiment types."""
        mock_bruker_class.return_value = mock_bruker_data
        
        converter = BrukerToJSONConverter(temp_directory)
        
        user_selections = {
            "30": {"experimentType": "Unknown", "procno": "1"}
        }
        
        json_data = converter.convert_to_json(
            user_selections,
            ml_consent=False,
            simulated_annealing=False
        )
        
        # Unknown experiments should be skipped
        assert "Unknown_0