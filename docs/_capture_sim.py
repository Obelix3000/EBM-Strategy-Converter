"""
Erzeugt einen aussagekräftigen Simulations-Screenshot mit sichtbarer Hitze-Spur.

Treibt die echte Simulation der MainWindow, hält sie bei ~50 % Fortschritt an
(Sim-Timer gestoppt, Bild bleibt stehen) und grabt das Fenster.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

import desktop_app  # noqa: E402
from src.pipeline import ZipSession  # noqa: E402


OUT_DIR = os.path.join(ROOT, "docs", "screenshots")
ZIP_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ.get("TEMP", "."), "20260408_5Cubes_0_Rotation.zip"
)


def process(ms: int) -> None:
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec()


def wait_preview(win, timeout_ms: int = 20000) -> None:
    elapsed = 0
    while (win.preview_worker_active or win.preview_pending) and elapsed < timeout_ms:
        process(100)
        elapsed += 100
    process(600)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    desktop_app.apply_light_theme(app)  # gleiches helles Theme wie die echte App
    win = desktop_app.MainWindow()
    win.resize(1500, 950)
    win.show()
    process(1200)

    win.session = ZipSession.from_zip(ZIP_PATH)
    win.zip_path_label.setText(ZIP_PATH)
    win._populate_infill_list()
    win._update_stats()

    # Eine einzelne, gut gefüllte Schicht wählen.
    mid = len(win.session.infill_files) // 2
    win._set_selected_index(mid)
    # Nur Punkte zeigen (klarere Hitze-Spur), Standard-Strategie.
    win.segmentation_combo.setCurrentText("Keine Segmentierung")
    win.micro_combo.setCurrentText("Raster (Zick-Zack)")
    win.preview_mode_combo.setCurrentText("Punkte")
    win._update_strategy_controls()
    win._request_preview()
    wait_preview(win)

    # Kamera näher heranzoomen, damit die Hitze-Spur sichtbar wird.
    cam = win.preview_canvas.view.camera

    # Simulation: moderate Geschwindigkeit, lange Hitze-Spur (gut sichtbarer
    # warmer Verlauf rot→orange→gold vor den hell zurücktretenden Punkten).
    win.sim_speed_spin.setValue(25)
    win.sim_decay_spin.setValue(300)
    win._start_simulation()

    # Warten bis Sim-Daten geladen sind und die Simulation läuft.
    waited = 0
    while not win.sim_running and waited < 10000:
        process(100)
        waited += 100

    # Kamera auf die aktive Schicht (einzelner Würfel) zentrieren und passend
    # heranzoomen – die Würfel liegen abseits des Ursprungs, sonst erscheint die
    # Schicht klein in der Plattenmitte.
    if win.sim_points_xyz is not None and len(win.sim_points_xyz):
        pts = win.sim_points_xyz
        c = pts.mean(axis=0)
        cam.center = (float(c[0]), float(c[1]), float(c[2]))
        extent = float(np.ptp(pts[:, :2]))  # Spannweite in XY
        cam.distance = max(extent * 2.0, 22.0)
        process(300)

    # Bis ca. 50 % Fortschritt laufen lassen.
    if win.sim_points_xyz is not None:
        target = len(win.sim_points_xyz) // 2
        guard = 0
        while win.sim_running and win.sim_index < target and guard < 30000:
            process(50)
            guard += 50

    # Sim-Timer anhalten -> Bild friert beim aktuellen "heißen" Punkt ein,
    # ohne dass _stop_simulation eine Vorschau-Neuberechnung auslöst.
    win.sim_timer.stop()
    process(400)
    pix = win.grab()
    path = os.path.join(OUT_DIR, "05_simulation.png")
    pix.save(path)
    print(f"gespeichert: 05_simulation.png  ({pix.width()}x{pix.height()})  "
          f"Index {win.sim_index}/{len(win.sim_points_xyz) if win.sim_points_xyz is not None else 0}")

    win.session.cleanup()
    app.quit()


if __name__ == "__main__":
    main()
