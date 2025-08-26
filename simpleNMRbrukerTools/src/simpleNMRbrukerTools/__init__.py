"""
SimpleNMR Bruker Tools
"""
__version__ = "1.0.0"

# Import submodules to make them available
try:
    from . import core
    from . import gui
    from . import parsers
    from . import utils
except ImportError:
    pass  # Handle gracefully if modules don't exist yet