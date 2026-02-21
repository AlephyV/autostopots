import sys
from pathlib import Path

# When running as a PyInstaller bundle, __file__ points inside the temp extraction
# dir. Use sys.executable (the .exe path) to find the real working directory.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = _BASE_DIR / "config.json"


def get_chromium_executable() -> str | None:
    """
    In frozen mode: returns the path to the Chromium bundled inside the .exe.
    In dev mode: returns None so Playwright uses its default installed browser.
    """
    if not getattr(sys, "frozen", False):
        return None
    # chrome.exe lives directly under the bundled chromium/ dir regardless of original folder name
    path = Path(sys._MEIPASS) / "chromium" / "chrome.exe"
    return str(path) if path.exists() else None
