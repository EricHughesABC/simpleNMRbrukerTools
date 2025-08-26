# src/__init__.py
"""
SimpleNMR Bruker Tools
"""
__version__ = "1.0.0"

# Import everything from subdirectories into the main namespace
try:
    from core import *
except ImportError:
    pass

try:
    from gui import *
except ImportError:
    pass
    
try:
    from parsers import *
except ImportError:
    pass
    
try:
    from utils import *
except ImportError:
    pass

try:
    from topspin_interface import *
except ImportError:
    pass

# Also make submodules available
try:
    from . import core
    from . import gui
    from . import parsers  
    from . import utils
    from . import topspin_interface
except ImportError:

    pass
