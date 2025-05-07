import importlib
import sys
import subprocess
from pathlib import Path

def check_requirements(requirements_path="requirements.txt"):
    """Check if all requirements are installed."""
    if not Path(requirements_path).exists():
        print(f"Error: {requirements_path} not found.")
        sys.exit(1)

    missing_packages = []
    with open(requirements_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            package = line.split("==")[0]
            try:
                importlib.import_module(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(line)

    if missing_packages:
        print("\nThe following packages are missing:")
        for pkg in missing_packages:
            print(f"  {pkg}")
        print("\nPlease install them with:")
        print(f"  pip3 install -r {requirements_path}")
        sys.exit(1)

if __name__ == "__main__":
    #check_requirements()
    from gui.main_window import start_gui
    start_gui()