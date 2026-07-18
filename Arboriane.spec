# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# Les modules de routes/services sont importés dynamiquement (routes.charger_modules
# fait « from routes import (...) »). On force l'inclusion de TOUS les sous-modules
# pour qu'aucune route ne manque à l'exe (ex. depots, lieux_ref, dates).
_hidden = (collect_submodules("routes") + collect_submodules("services")
           + collect_submodules("core")
           # TOUS les codecs (encodings.cp1252, cp850, latin_1, mac_roman…) : un
           # utilisateur a eu des accents en « � » à l'import ANSI, symptôme d'un
           # codec cp1252 absent de l'exe figé. On force leur inclusion.
           + collect_submodules("encodings"))

a = Analysis(
    ['lanceur.py'],
    pathex=[],
    binaries=[],
    datas=[('web', 'web')],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Arboriane',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='web\\favicon.ico',
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Arboriane',
)
