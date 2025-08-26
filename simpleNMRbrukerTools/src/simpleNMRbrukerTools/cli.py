import os
import sys
import shutil
from pathlib import Path

# from src import simpleNMRbrukerTools


try:
    from bruker.api.topspin import Topspin
    from bruker.data.nmr import *
except ImportError as e:
    print("Error importing Bruker modules:", e)
    print("\n\nPlease ensure that Bruker Python Modules are installed and accessible.")
    # exit script
    sys.exit(1)

# Import submodules
import simpleNMRbrukerTools   

from simpleNMRbrukerTools import core
from simpleNMRbrukerTools import gui
from simpleNMRbrukerTools import parsers
from simpleNMRbrukerTools import utils

from simpleNMRbrukerTools.core.json_converter import BrukerToJSONConverter
from simpleNMRbrukerTools.core.data_reader import BrukerDataDirectory  
from simpleNMRbrukerTools.config import EXPERIMENT_CONFIGS

def setup_topspin():

    # Initialize Topspin
    top = Topspin()
    
    # Check if Topspin is running
    try:
        topspinDir_str = top.getInstallationDirectory()
        print("Topspin installation directory:", topspinDir_str)
        topspinDir = Path(topspinDir_str)

    except Exception as e:
        print("Error getting Topspin installation directory:", e)
        print("\n\nPlease ensure that Topspin is running and run the script again.")
        sys.exit(1)

    # create directories
    package_dir = Path(simpleNMRbrukerTools.__file__).parent
    topspinGUIdir = Path(package_dir / "topspin_interface")
    topspinPROGSdir = Path(package_dir / "topspin_programs")

    # topspin directories
    py3userDir = Path(topspinDir / "exp" / "stan" / "nmr" / "py3" / "user")
    propsDir = Path(topspinDir / "classes" / "prop" / "flowbars")

    # check if py3userDir exists
    if not py3userDir.exists():
        print("Error: Python 3 user directory does not exist:\n\t", py3userDir)
        sys.exit(1)

    # check if propsDir exists
    if not propsDir.exists():
        print("Error: Props directory does not exist:\n\t", propsDir)
        sys.exit(1)

    if not topspinGUIdir.exists():
        print("Error: Topspin GUI directory does not exist:\n\t", topspinGUIdir)
        sys.exit(1)

    # copy *.prop files from topspinGUIdir to py3userDir
    for file in topspinGUIdir.glob("*.prop"):
        if file.is_file():
            target_file = propsDir / file.name
            print(f"Copying {file} to {target_file}")
            # Here you would add the actual file copying logic
            # For example, using shutil.copy(file, target_file)
            shutil.copy(file, target_file)

    # copy *.py files from topspinPROGSdir to propsDir
    for file in topspinPROGSdir.glob("*.py"):
        # skip __init__.py files
        if file.is_file() and file.name != "__init__.py":
            target_file = py3userDir / file.name
            print(f"Copying {file} to {target_file}")
            shutil.copy(file, target_file)

def uninstall_topspin():
    pass

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        sys.exit(uninstall_topspin())
    else:
        sys.exit(setup_topspin())