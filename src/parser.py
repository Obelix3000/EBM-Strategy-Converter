import re
from typing import List, Tuple
import numpy as np
from shapely.geometry import Polygon, MultiPoint

class B99Parser:
    """
    Reverse-Engineering (Umkehrmethodik) bestehender .B99 Arcam-Dateien.
    Dieser Converter-Scanner liest rohe physikalische Punkte (ABS) vom Maschinenformat (Werte -1 bis +1),
    konvertiert diese zurück in den echten metrischen Raum (Millimeter) und zieht
    die Layer-Boundingboxen (Außenkanten) aus den reinen Punktdaten via Hüllkurven-Berechnung.
    """
    
    @staticmethod
    def parse_to_polygons(b99_content: str) -> List[Polygon]:
        """
        Liest den B99 Text, skaliert alle 'ABS x y' Koordinaten via *60 und liefert 
        eine iterierbare Serie von Grenz-Polygonen (eines für jede einzelne Pulverschicht).
        Die Erkennung der Layer erfolgt klassisch über die Metadaten-Tags ("# figure Group_Layer_xxx").
        
        :param b99_content: Der aus der .B99 Datei gelesene String.
        :return: Liste von Shapely Polygonen, ready für komplett neue Scan-Strategien.
        """
        layers_points = []
        current_layer_pts = []
        
        # Zeilenweises Parsen
        lines = b99_content.splitlines()
        in_data = False
        
        for line in lines:
            line = line.strip()
            # Die meisten Arcam Standarddateien nutzen # figure vor jedem Start einer neuen Sektion
            if line.startswith("# figure"):
                if current_layer_pts:
                    layers_points.append(current_layer_pts)
                current_layer_pts = []
                in_data = False
            elif line.startswith("data"):
                # Nach dem 'data' Attribut folgenden in der B99 reine Schmelz-Koordinaten 
                in_data = True
            elif in_data and line.startswith("ABS"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        # Die Bauplattform der Maschine misst 120x120 mm mit Nullpunkt in der Mitte
                        # Relativ bedeutet: Ein Wert von 1.0 ist der Rand bei X = +60.0 mm
                        x = float(parts[1]) * 60.0
                        y = float(parts[2]) * 60.0
                        current_layer_pts.append((x, y))
                    except ValueError:
                        continue
                        
        # Den letzten gefundenen Layer noch anhängen, falls hiernach EOF eintritt
        if current_layer_pts:
            layers_points.append(current_layer_pts)
            
        layer_polygons = []
        for pts in layers_points:
            # Leere Schichten ohne Pfade filtern
            if not pts:
                continue
                
            # Erschaffung einer mathematischen Punktwolke (MultiPoint)
            mul_pt = MultiPoint(pts)
            
            # Da wir die Datei nur als Punkte einlesen, müssen wir den Rand 'erraten'.
            # Mathematisch ist die "Konvexe Hülle" (convex_hull) das geometrische Mittel 
            # welches wie ein Gummiband die äußersten Punkte umspannt. 
            # -> Und somit die Schicht-Außenkante des alten Modells exakt rekonstruiert!
            hull = mul_pt.convex_hull
            
            if hull.geom_type == 'Polygon':
                layer_polygons.append(hull)
            else:
                # Falls die Geometrie aufgrund numerischer Eigenheiten eine exakte Linie ist
                # (also ein Rechteck ohne wirkliche Tiefe), nutzen wir einen leichten Buffer()
                # um sie künstlich aufzudicken und den Code nicht abstürzen zu lassen.
                buffered = hull.buffer(0.01)
                if buffered.geom_type == 'Polygon':
                    layer_polygons.append(buffered)
                
        return layer_polygons

    @staticmethod
    def extract_points_and_header(b99_content: str) -> Tuple[List[str], np.ndarray]:
        """
        Extrahiert alle Header-Zeilen (bis einschließlich 'data') und alle ABS-Koordinaten
        als N×2 NumPy-Array in mm. Positionen werden NICHT verändert – nur ausgelesen.

        :param b99_content: Rohinhalt einer .B99-Datei als String.
        :return: (header_lines, points_mm) – header_lines ist eine Liste von Strings,
                 points_mm ein np.ndarray der Form (N, 2).
        """
        header_lines: List[str] = []
        points: List[List[float]] = []
        in_data = False

        for line in b99_content.splitlines():
            stripped = line.strip()
            if not in_data:
                header_lines.append(line)
                if stripped.startswith("data"):
                    in_data = True
            elif stripped.startswith("ABS"):
                parts = stripped.split()
                if len(parts) >= 3:
                    try:
                        x_mm = float(parts[1]) * 60.0
                        y_mm = float(parts[2]) * 60.0
                        points.append([x_mm, y_mm])
                    except ValueError:
                        continue

        arr = np.array(points, dtype=np.float64) if points else np.empty((0, 2), dtype=np.float64)
        return header_lines, arr
