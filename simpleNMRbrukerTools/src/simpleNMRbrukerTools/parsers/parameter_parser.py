# """
# bruker_nmr/src/core/parameter_parser.py
# """
# import re
# from pathlib import Path
# from typing import Dict, Any, Union


# class BrukerParameterFile:
#     """
#     Parses Bruker parameter files (acqus, procs, clevels, etc.) with dictionary-like access.
    
#     Attributes:
#         file_path (Path): Path to the parameter file
#         parameters (Dict[str, Any]): Parsed parameters
#         raw_content (str): Raw file content
#     """
    
#     def __init__(self, file_path: Union[str, Path]):
#         """
#         Initialize parser with parameter file.
        
#         Args:
#             file_path: Path to Bruker parameter file
            
#         Raises:
#             FileNotFoundError: If parameter file doesn't exist
#         """
#         self.file_path = Path(file_path)
#         self.parameters = {}
#         self.raw_content = ""
        
#         if not self.file_path.exists():
#             raise FileNotFoundError(f"Parameter file not found: {file_path}")
        
#         self._parse_file()
    
#     def _parse_file(self) -> None:
#         """Parse the parameter file and extract all parameters."""
#         with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
#             self.raw_content = f.read()
        
#         lines = self.raw_content.split('\n')
#         i = 0
        
#         while i < len(lines):
#             line = lines[i].strip()
            
#             if self._should_skip_line(line):
#                 i += 1
#                 continue
            
#             if line.startswith('##$'):
#                 param_name, value, i = self._parse_parameter(lines, i)
#                 if param_name:
#                     self.parameters[param_name] = value
#             else:
#                 i += 1
    
#     def _should_skip_line(self, line: str) -> bool:
#         """Check if line should be skipped during parsing."""
#         return (line.startswith('$$') or 
#                 line.startswith('##END') or 
#                 not line)
    
#     def _parse_parameter(self, lines: list, start_index: int) -> tuple:
#         """
#         Parse a single parameter that may span multiple lines.
        
#         Returns:
#             tuple: (param_name, value, next_index)
#         """
#         line = lines[start_index].strip()
        
#         match = re.match(r'##\$([^=]+)=\s*(.*)', line)
#         if not match:
#             return None, None, start_index + 1
        
#         param_name = match.group(1)
#         value_str = match.group(2)
        
#         # Handle array parameters
#         if self._is_array_parameter(param_name):
#             array_values, next_index = self._parse_array_values(lines, start_index, value_str)
#             base_name = re.match(r'([^(]+)', param_name).group(1)
#             return base_name, array_values, next_index
        
#         # Single value parameter
#         parsed_value = self._convert_value(value_str)
#         return param_name, parsed_value, start_index + 1
    
#     def _is_array_parameter(self, param_name: str) -> bool:
#         """Check if parameter is an array type."""
#         return '(' in param_name and ')' in param_name
    
#     def _parse_array_values(self, lines: list, start_index: int, initial_value: str) -> tuple:
#         """Parse array values that may span multiple lines."""
#         values = []
#         current_line = initial_value
#         i = start_index
        
#         while i < len(lines):
#             line_values = current_line.strip().split()
#             values.extend(line_values)
            
#             i += 1
#             if i < len(lines):
#                 next_line = lines[i].strip()
#                 if next_line.startswith('##') or not next_line:
#                     break
#                 current_line = next_line
#             else:
#                 break
        
#         converted_values = [self._convert_value(v) for v in values]
#         return converted_values, i
    
#     def _convert_value(self, value_str: str) -> Union[str, int, float, bool]:
#         """Convert string value to appropriate Python type."""
#         value_str = value_str.strip()
        
#         if not value_str:
#             return ""
        
#         # Handle angle brackets
#         if value_str.startswith('<') and value_str.endswith('>'):
#             return value_str[1:-1]
        
#         # Handle boolean values
#         if value_str.lower() in ['yes', 'no']:
#             return value_str.lower() == 'yes'
        
#         # Try numeric conversion
#         try:
#             if '.' not in value_str and 'e' not in value_str.lower():
#                 return int(value_str)
#             else:
#                 return float(value_str)
#         except ValueError:
#             return value_str
    
#     # Dictionary-like interface
#     def get(self, key: str, default: Any = None) -> Any:
#         """Get parameter value with default."""
#         return self.parameters.get(key, default)
    
#     def __getitem__(self, key: str) -> Any:
#         """Get parameter value."""
#         return self.parameters[key]
    
#     def __contains__(self, key: str) -> bool:
#         """Check if parameter exists."""
#         return key in self.parameters
    
#     def keys(self):
#         """Get parameter keys."""
#         return self.parameters.keys()

"""
bruker_nmr/src/core/parameter_parser.py
"""
import re
from pathlib import Path
from typing import Dict, Any, Union


class BrukerParameterFile:
    """
    Parses Bruker parameter files (acqus, procs, clevels, etc.) with dictionary-like access.
    
    Attributes:
        file_path (Path): Path to the parameter file
        parameters (Dict[str, Any]): Parsed parameters
        raw_content (str): Raw file content
    """
    
    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize parser with parameter file.
        
        Args:
            file_path: Path to Bruker parameter file
            
        Raises:
            FileNotFoundError: If parameter file doesn't exist
        """
        self.file_path = Path(file_path)
        self.parameters = {}
        self.raw_content = ""
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Parameter file not found: {file_path}")
        
        self._parse_file()
    
    def _parse_file(self) -> None:
        """Parse the parameter file and extract all parameters."""
        with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.raw_content = f.read()
        
        lines = self.raw_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if self._should_skip_line(line):
                i += 1
                continue
            
            if line.startswith('##$'):
                param_name, value, i = self._parse_parameter(lines, i)
                if param_name:
                    self.parameters[param_name] = value
            else:
                i += 1
    
    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped during parsing."""
        return (line.startswith('$$') or 
                line.startswith('##END') or 
                not line)
    
    def _parse_parameter(self, lines: list, start_index: int) -> tuple:
        """
        Parse a single parameter that may span multiple lines.
        
        Returns:
            tuple: (param_name, value, next_index)
        """
        line = lines[start_index].strip()
        
        match = re.match(r'##\$([^=]+)=\s*(.*)', line)
        if not match:
            return None, None, start_index + 1
        
        param_name = match.group(1)
        value_str = match.group(2)
        
        # Handle array parameters
        if self._is_array_parameter(value_str):
            array_values, next_index = self._parse_array_values(lines, start_index)
            base_name = re.match(r'([^(]+)', param_name).group(1)
            return base_name, array_values, next_index
        
        # Single value parameter
        parsed_value = self._convert_value(value_str)
        return param_name, parsed_value, start_index + 1
    
    def _is_array_parameter(self, param_name: str) -> bool:
        """Check if parameter is an array type."""
        return '(' in param_name and ')' in param_name
    
    def _parse_array_values(self, lines: list, start_index: int) -> tuple:
        """Parse array values that may span multiple lines."""
        values = []
        i = start_index + 1  # Skip the parameter definition line
        
        # Continue reading lines until we hit another parameter or end
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop if we hit another parameter, comment, or end
            if (line.startswith('##$') or 
                line.startswith('$$') or 
                line.startswith('##END') or
                not line):
                break
            
            # Split the line and add values
            line_values = line.split()
            values.extend(line_values)
            i += 1
        
        # Convert all values to appropriate types
        converted_values = [self._convert_value(v) for v in values]
        return converted_values, i
    
    def _convert_value(self, value_str: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate Python type."""
        value_str = value_str.strip()
        
        if not value_str:
            return ""
        
        # Handle angle brackets
        if value_str.startswith('<') and value_str.endswith('>'):
            return value_str[1:-1]
        
        # Handle boolean values
        if value_str.lower() in ['yes', 'no']:
            return value_str.lower() == 'yes'
        
        # Try numeric conversion
        try:
            if '.' not in value_str and 'e' not in value_str.lower():
                return int(value_str)
            else:
                return float(value_str)
        except ValueError:
            return value_str
    
    # Dictionary-like interface
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default."""
        return self.parameters.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get parameter value."""
        return self.parameters[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if parameter exists."""
        return key in self.parameters
    
    def keys(self):
        """Get parameter keys."""
        return self.parameters.keys()


# Example usage:
if __name__ == "__main__":
    # Test with your parameter file
    parser = BrukerParameterFile("paste.txt")
    
    # Now AMP should contain the actual array values
    print("AMP values:", parser["AMP"])
    print("Number of AMP values:", len(parser["AMP"]))
    
    # Test other arrays
    print("GPZ values:", parser["GPZ"])
    print("CNST values:", parser["CNST"])