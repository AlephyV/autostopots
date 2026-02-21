from pathlib import Path
import customtkinter
from PyInstaller.utils.hooks import collect_all

block_cipher = None
ctk_path = str(Path(customtkinter.__file__).parent)

# collect_all includes Python code, data files (driver binaries) and hidden imports
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pw_binaries,
    datas=[
        (ctk_path, "customtkinter"),
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
    icon=None,  # coloque o caminho de um .ico aqui se quiser
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
