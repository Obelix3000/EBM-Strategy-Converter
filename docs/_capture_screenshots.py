"""
Automatisiert die Desktop-App und erzeugt echte Screenshots für die Doku.

Treibt die echte MainWindow programmatisch:
  - lädt das Test-ZIP (ohne Dateidialog),
  - setzt Strategie-Parameter,
  - wartet auf Vorschau/Simulation,
  - speichert echte Fenster-Screenshots per QWidget.grab().

Start (aus Projektwurzel):
    .venv_doc\\Scripts\\python.exe docs\\_capture_screenshots.py <pfad-zur-zip>
"""

import os
import sys

# Projektwurzel in den Pfad, damit `import desktop_app` / `src.*` funktioniert.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6 import QtCore, QtWidgets, QtGui  # noqa: E402

import desktop_app  # noqa: E402
from src.pipeline import ZipSession  # noqa: E402


OUT_DIR = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

ZIP_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ.get("TEMP", "."), "20260408_5Cubes_0_Rotation.zip"
)


def process(ms: int) -> None:
    """Event-Loop für `ms` Millisekunden laufen lassen (Worker, Repaint, VisPy)."""
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_preview(win, timeout_ms: int = 20000) -> None:
    """Wartet, bis der laufende Vorschau-Worker fertig ist."""
    elapsed = 0
    step = 100
    while (win.preview_worker_active or win.preview_pending) and elapsed < timeout_ms:
        process(step)
        elapsed += step
    process(600)  # VisPy einen Frame rendern lassen


def grab(widget, name: str) -> None:
    process(400)
    pix = widget.grab()
    path = os.path.join(OUT_DIR, name)
    pix.save(path)
    print(f"  gespeichert: {name}  ({pix.width()}x{pix.height()})")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    desktop_app.apply_light_theme(app)  # gleiches helles Theme wie die echte App
    win = desktop_app.MainWindow()
    win.resize(1500, 950)
    win.show()
    process(1200)  # VisPy-Canvas initialisieren

    # 1) Startzustand (leeres Projekt)
    grab(win, "01_startfenster.png")

    # --- ZIP laden (ohne Dateidialog) ---------------------------------------
    print(f"Lade ZIP: {ZIP_PATH}")
    win.session = ZipSession.from_zip(ZIP_PATH)
    win.zip_path_label.setText(ZIP_PATH)
    win._populate_infill_list()
    win._update_stats()
    win._request_preview()
    wait_preview(win)

    # 2) Geladenes Projekt – Standardstrategie, Standard-Layer
    grab(win, "02_projekt_geladen.png")

    # --- Mittlere Schicht wählen (mehr Punkte, schöneres Bild) --------------
    mid = len(win.session.infill_files) // 2
    win._set_selected_index(mid)
    wait_preview(win)

    # --- Strategie: Schachbrett-Segmentierung + Raster, sichtbare Rotation ---
    win.segmentation_combo.setCurrentText("Schachbrett (Island)")
    win.seg_size_spin.setValue(8.0)
    win.micro_combo.setCurrentText("Raster (Zick-Zack)")
    win.rotation_spin.setValue(67.0)
    win.preview_mode_combo.setCurrentText("Beides")
    win._update_strategy_controls()
    win._request_preview()
    wait_preview(win)

    # 3) Strategie konfiguriert + Vorschau
    grab(win, "03_strategie_vorschau.png")

    # --- Nur das Bedien-Panel (Sidebar) als Detail-Screenshot ---------------
    # Splitter: links Canvas, rechts ScrollArea mit den Panels.
    splitter = win.centralWidget()
    scroll = splitter.widget(1)
    grab(scroll, "04_bedienpanel.png")

    # 4) Simulation starten und einen Frame mit "heißem" Punkt einfangen
    win.sim_speed_spin.setValue(200)
    win.sim_decay_spin.setValue(80)
    win._start_simulation()
    # Sim-Daten laden (Worker) + einige Ticks laufen lassen
    process(3000)
    grab(win, "05_simulation.png")
    win._stop_simulation()
    wait_preview(win)

    # --- Export-Panel-Ausschnitt (Ausgabeordner sichtbar) -------------------
    grab(scroll, "06_export_panel.png")

    win.session.cleanup()
    print("Fertig.")
    app.quit()


if __name__ == "__main__":
    main()
