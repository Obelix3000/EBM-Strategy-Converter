import re
from typing import List
import numpy as np


class B99Exporter:
    """
    Schreibt neu geordnete Punktdaten in das Arcam .B99-Dateiformat.
    Der originale Header (alle Zeilen bis einschließlich 'data') wird
    unverändert übernommen; nur die ABS-Koordinaten werden ersetzt und
    das Feld 'Number Points' im Header auf die tatsächliche Punktzahl
    nachgeführt (siehe _sync_point_count).
    """

    _NUM_POINTS_RE = re.compile(r"(Number Points\s*=\s*)\d+")

    @staticmethod
    def _sync_point_count(header_lines: List[str], n_points: int) -> List[str]:
        """Setzt 'Number Points=<N>' im Header auf die tatsächlich geschriebene
        Punktzahl. Notwendig, weil Segmentierungs-Overlap und Ghost Beam die
        Punktzahl gegenüber dem Original verändern – bleibt der Header-Wert stehen,
        meldet der Maschinen-Controller (MMC) beim Laden einen FIG_LOAD-Fehler
        (Header-Pufferreservierung passt nicht zur tatsächlichen Punktzahl).
        Zeilen ohne 'Number Points'-Feld bleiben unverändert."""
        return [
            B99Exporter._NUM_POINTS_RE.sub(rf"\g<1>{n_points}", line)
            for line in header_lines
        ]

    @staticmethod
    def write_reordered_b99(header_lines: List[str], points_mm: np.ndarray) -> str:
        """
        Erzeugt den kompletten Dateiinhalt einer B99-Datei aus dem originalen Header
        und neu geordneten Koordinaten.

        Koordinaten werden mit 17 signifikanten Stellen ausgegeben (wie im Original).
        Zeilenenden: \\r\\n (Windows-Format wie in Arcam-Referenzdateien).

        :param header_lines: Liste der Original-Header-Zeilen (inkl. 'data'-Zeile).
        :param points_mm:    np.ndarray (N, 2) mit Koordinaten in mm.
        :return:             Fertiger Dateiinhalt als String.
        """
        content = B99Exporter._sync_point_count(header_lines, len(points_mm))
        for x_mm, y_mm in points_mm:
            rx = x_mm / 60.0
            ry = y_mm / 60.0
            content.append(f"ABS {rx:.17g} {ry:.17g}")
        return "\r\n".join(content) + "\r\n"
