# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# vispy + shapely vollständig sammeln: deren Backends/Shader (vispy) bzw. die
# GEOS-DLLs (shapely) werden dynamisch geladen und vom Import-Graph allein nicht
# zuverlässig erfasst.
for _pkg in ('vispy', 'shapely'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# scipy wird bewusst NICHT komplett gesammelt. Die App nutzt ausschließlich
# scipy.spatial.KDTree (Greedy-/Dispersions-Strategien). collect_all('scipy')
# zog vorher das gesamte Paket (optimize/stats/signal/io/… ~85 MB) in die EXE.
# Stattdessen erfasst der Import-Graph scipy.spatial selbst; die nativen
# OpenBLAS-DLLs hängen als PE-Abhängigkeit an scipy.spatial._ckdtree und werden
# über die scipy-Hook/Abhängigkeitsanalyse mitgenommen.
hiddenimports += ['scipy.spatial', 'scipy.spatial.transform']


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Schwergewichtige Pakete/Module, die die App NICHT nutzt – sonst blähen sie
    # die EXE auf. Real importiert die App nur: PySide6 (QtCore/QtGui/QtWidgets/
    # QtOpenGL), vispy, numpy, shapely und scipy.spatial.
    excludes=[
        # Fremde Schwergewichte (nur über optionale Backends eingezogen)
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'tensorboard',
        'sklearn', 'scikit-learn',
        'sympy', 'pandas', 'matplotlib', 'cv2',
        'dask', 'cupy',
        'IPython', 'ipykernel', 'jupyter', 'jupyter_client', 'notebook',
        # Pillow: vispy.io importiert PIL nur lazy (Bild-I/O), die App ruft das
        # nie auf -> ~14 MB sparen.
        'PIL',
        # Ungenutzte scipy-Subpakete (App nutzt nur scipy.spatial).
        'scipy.optimize', 'scipy.stats', 'scipy.signal', 'scipy.io',
        'scipy.interpolate', 'scipy.integrate', 'scipy.ndimage',
        'scipy.cluster', 'scipy.odr', 'scipy.datasets', 'scipy.misc',
        'scipy.fft', 'scipy.fftpack',
        # Ungenutzte Qt-Module (App ist eine reine QtWidgets-Anwendung).
        'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtQuick3D',
        'PySide6.QtQuickWidgets', 'PySide6.QtQuickControls2',
        'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender',
        # Hinweis: PySide6.QtTest NICHT ausschließen – das vispy-PySide6-Backend
        # importiert es auf Modulebene (vispy/app/backends/_pyside6.py).
        'PySide6.QtSql', 'PySide6.QtDesigner',
        'PySide6.QtBluetooth', 'PySide6.QtSensors', 'PySide6.QtPositioning',
    ],
    noarchive=False,
    optimize=0,
)

# --- Nachträgliches Trimmen von Artefakten, die die Qt-Hook trotzdem einsammelt ---
# (Module-Excludes greifen nicht auf reine Daten-/DLL-Einträge.)
_QT_DROP_PREFIXES = (
    'qt6quick', 'qt6qml', 'qt6quick3d', 'qt6pdf', 'qt6charts',
    'qt6datavisualization', 'qt63d', 'qt6multimedia', 'qt6webengine',
    'qt6sql', 'qt6designer', 'qt6virtualkeyboard',
    # 'qt6test' bewusst NICHT droppen: Qt6Test.dll wird vom vispy-PySide6-Backend
    # (from PySide6 import QtTest) benötigt.
)


def _keep(entry) -> bool:
    dest = entry[0].replace('\\', '/').lower()
    # Qt-Übersetzungen (alle Sprachen) – die App ist deutsch/festverdrahtet (~6 MB).
    if '/translations/' in dest and dest.endswith('.qm'):
        return False
    base = os.path.basename(dest)
    if any(base.startswith(p) for p in _QT_DROP_PREFIXES):
        return False
    return True


a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]

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
