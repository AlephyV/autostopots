import sys
from pathlib import Path

# When running as a PyInstaller bundle, __file__ points inside the temp extraction
# dir. Use sys.executable (the .exe path) to find the real working directory.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = _BASE_DIR / "config.json"
