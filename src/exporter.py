from typing import List
import numpy as np


class B99Exporter:
    """
    Schreibt neu geordnete Punktdaten in das Arcam .B99-Dateiformat.
    Der originale Header (alle Zeilen bis einschließlich 'data') wird
    unverändert übernommen; nur die ABS-Koordinaten werden ersetzt.
    """

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
        content = list(header_lines)
        for x_mm, y_mm in points_mm:
            rx = x_mm / 60.0
            ry = y_mm / 60.0
            content.append(f"ABS {rx:.17g} {ry:.17g}")
        return "\r\n".join(content) + "\r\n"
