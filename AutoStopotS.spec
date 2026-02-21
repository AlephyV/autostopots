import glob
import os
from pathlib import Path
import customtkinter
from PyInstaller.utils.hooks import collect_all

block_cipher = None

ctk_path = str(Path(customtkinter.__file__).parent)

# Find the Chromium installed by `playwright install chromium`
_local = os.environ.get("LOCALAPPDATA", "")
_chromium_dirs = glob.glob(os.path.join(_local, "ms-playwright", "chromium-*", "chrome-win*"))
if not _chromium_dirs:
    raise SystemExit(
        "Chromium nao encontrado. Rode primeiro: playwright install chromium"
    )
chromium_src = _chromium_dirs[-1]  # use latest version

pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pw_binaries,
    datas=[
        (ctk_path, "customtkinter"),
        (chromium_src, "chromium"),   # bundled browser, no download needed
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
