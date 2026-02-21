from pathlib import Path
import customtkinter
import playwright
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ctk_path = str(Path(customtkinter.__file__).parent)

# Playwright Python modules + hidden imports
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")

# Playwright Node.js driver (node.exe + playwright CLI package).
# Must be at playwright/driver/ so compute_driver_executable() finds it.
pw_driver_src = str(Path(playwright.__file__).parent / "driver")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pw_binaries,
    datas=[
        (ctk_path, "customtkinter"),
        (pw_driver_src, "playwright/driver"),  # driver bundled explicitly
        *pw_datas,
    ],
    hiddenimports=[
        *pw_hiddenimports,
        "customtkinter",
        "openai",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="AutoStopotS",
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AutoStopotS",
)
