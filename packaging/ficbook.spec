# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the macOS Ficbook Downloader app."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent

datas = []
binaries = []
hiddenimports = []
for package in ("curl_cffi", "bs4", "PIL"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += [
    "ficbook_dl",
    "ficbook_dl.gui",
    "ficbook_dl.i18n",
    "ficbook_dl.download",
    "ficbook_dl.client",
    "ficbook_dl.parse",
    "ficbook_dl.formats",
    "ficbook_dl.formats.epub",
    "ficbook_dl.formats.fb2",
    "ficbook_dl.formats.txt",
    "ficbook_dl.formats.cover",
]

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Ficbook Downloader",
    console=False,
    argv_emulation=False,
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    name="Ficbook Downloader",
)

app = BUNDLE(
    coll,
    name="Ficbook Downloader.app",
    bundle_identifier="com.thanaton20.ficbook-downloader",
    info_plist={
        "CFBundleName": "Ficbook Downloader",
        "CFBundleDisplayName": "Ficbook Downloader",
        "CFBundleShortVersionString": "0.3.0",
        "CFBundleVersion": "0.3.0",
        "NSHighResolutionCapable": True,
    },
)
