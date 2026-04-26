# -*- mode: python ; coding: utf-8 -*-
# VolcanoEruptionMonitor.spec  —  Vedurocks Ltd 2026

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

HERE = Path(SPECPATH)

# ── Force-collect encodings ───────────────────────────────
enc_datas, enc_binaries, enc_hiddenimports = collect_all("encodings")

# ── Force-collect matplotlib (if installed) ───────────────
try:
    mpl_datas, mpl_binaries, mpl_hiddenimports = collect_all("matplotlib")
    print("✓ matplotlib found - will be bundled")
except Exception as e:
    mpl_datas, mpl_binaries, mpl_hiddenimports = [], [], []
    print(f"✗ matplotlib not found: {e}")

# ── Data files ────────────────────────────────────────────
added_files = list(enc_datas) + list(mpl_datas)
for fname in ("logo.png", "volcano.ico"):
    p = HERE / fname
    if p.exists():
        added_files.append((str(p), "."))

# ── Hidden imports ────────────────────────────────────────
hidden = (
    enc_hiddenimports
    + mpl_hiddenimports
    + collect_submodules("encodings")
    + [
        # Serial
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
        "serial.tools.list_ports_windows",
        "serial.tools.list_ports_posix",
        
        # PIL
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageDraw",
        
        # Requests
        "requests",
        "requests.adapters",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        
        # Tkinter
        "tkinter",
        "tkinter.ttk",
        "tkinter.font",
        
        # matplotlib TkAgg backend (explicit)
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends._tkagg",
        "matplotlib.backends._backend_tk",
        
        # Stdlib
        "json",
        "csv",
        "_csv",
        
        # PyInstaller dependencies - DO NOT EXCLUDE
        "pkg_resources",
        "setuptools",
    ]
)

a = Analysis(
    [str(HERE / "VolcanoEruptionMonitor.pyw")],
    pathex=[str(HERE)],
    binaries=list(enc_binaries) + list(mpl_binaries),
    datas=added_files,
    hiddenimports=hidden,
    excludes=[
        # Only exclude truly unused modules
        "doctest",
        "pydoc",
        "xmlrpc",
        "ftplib",
        "imaplib",
        "poplib",
        "smtplib",
        "antigravity",
        "turtle",
        "turtledemo",
        "tkinter.test",
        "test",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VolcanoEruptionMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(HERE / "volcano.ico") if (HERE / "volcano.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VolcanoEruptionMonitor",
)
