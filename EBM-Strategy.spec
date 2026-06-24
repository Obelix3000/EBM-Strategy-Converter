# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('vispy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('shapely')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Schwergewichtige Pakete, die die App NICHT nutzt. Sie werden nur über
    # optionale Backends von scipy (array_api_compat: torch/dask/cupy) bzw.
    # zufällig in der Umgebung installierte Pakete eingezogen und blähen die EXE
    # auf. Die App importiert real nur: PySide6, vispy, numpy, shapely, scipy.spatial.
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'tensorboard',
        'sklearn', 'scikit-learn',
        'sympy',
        'pandas',
        'matplotlib',
        'cv2',
        'dask', 'cupy',
        'IPython', 'ipykernel', 'jupyter', 'jupyter_client', 'notebook',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EBM-Strategy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
