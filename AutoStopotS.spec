import sys
from pathlib import Path
import customtkinter

block_cipher = None
ctk_path = str(Path(customtkinter.__file__).parent)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        (ctk_path, "customtkinter"),
    ],
    hiddenimports=[
        "customtkinter",
        "openai",
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AutoStopotS",
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # sem janela de console
    icon=None,      # coloque o caminho de um .ico aqui se quiser
)
