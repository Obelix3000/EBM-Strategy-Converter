import math
from typing import Any
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.affinity import rotate, translate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class RasterStrategy(BaseScanStrategy):
    """
    Klassische Raster/Hatch Strategie.
    Füllt ein gegebenes Polygon mit parallelen Linien in einem einstellbaren Winkel.
    (Meist 67 Grad Rotation pro Schicht für das Verhindern von Eigenspannungen).
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        # Standardparameter sicherstellen
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        
        # Umrechnung von Mikrometern in Millimeter (Standardlängeneinheit der Maschine)
        hatch_spacing = hatch_spacing_um / 1000.0
        point_spacing = point_spacing_um / 1000.0
        
        scan_path = ScanPath(segments=[])
        
        # Leere Polygone ignorieren
        if polygon.is_empty or hatch_spacing <= 0:
            return scan_path

        # Das Polygon wird rotierend in die Horizontale der Rechenebene gezwungen.
        # Dies erlaubt uns, simple gerade Linien parallel zur X-Achse zu generieren!
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        
        # Den umhüllenden Bereich (Bounding Box) extrahieren
        minx, miny, maxx, maxy = rotated_poly.bounds
        
        # Bounding-Box minimal vergrößern, um Kantenüberlappungen zu garantieren
        minx -= hatch_spacing
        maxx += hatch_spacing
        miny -= hatch_spacing
        maxy += hatch_spacing
        
        # Generierung aller horizontalen Y-Koordinaten
        y_coords = np.arange(miny, maxy, hatch_spacing)
        
        lines = []
        for i, y in enumerate(y_coords):
            line = LineString([(minx, y), (maxx, y)])
            # Verschneiden der endlosen Linie mit den realen Polygon-Grenzen
            intersection = rotated_poly.intersection(line)
            
            if intersection.is_empty:
                continue
                
            # Wenn das Polygon Löcher (Holes) hat, kann die Intersection aus mehreren separaten Liniensplittern bestehen.
            geom_type = intersection.geom_type
            if geom_type == 'LineString':
                lines.append((i, intersection))
            elif geom_type == 'MultiLineString':
                for sub_line in intersection.geoms:
                    if sub_line.geom_type == 'LineString':
                        lines.append((i, sub_line))
        lines.sort(key=lambda item: (item[0], item[1].bounds[0]))
        
        # Die gerasterten Linien zurück in den originalen Koordinatenraum bringen.
        # Ein "Schlangen"-Muster (Zick-Zack) durch Alternieren der Richtung herstellen.
        for i, (idx, line) in enumerate(lines):
            flip_line = (i % 2 == 1)
            
            # Rotation der gezeichneten Vektoren wieder zurück in den ursprünglichen Layer-Winkel (z.B. +67 Grad)
            orig_line = rotate(line, rotation_angle_deg, origin=polygon.centroid, use_radians=False)
            
            # Diskretisieren der zusammenhängenden Linie in Einzelpunkte für das .B99 Format
            length = orig_line.length
            distances = np.arange(0, length, point_spacing)
            
            points_list = []
            for d in distances:
                pt = orig_line.interpolate(d)
                points_list.append((pt.x, pt.y))
                
            # Garantieren, dass das Ende der Linie exakt mit dem Polygon abschließt, falls der Abstand nicht perfekt aufgeht
            if not np.isclose(length, distances[-1] if len(distances)>0 else -1):
                pt = orig_line.interpolate(length)
                points_list.append((pt.x, pt.y))
                
            # Zick-Zack Umkehroperation
            if flip_line:
                points_list.reverse()
                
            # Einfügen als "On-Beam" Segment
            scan_path.add_segment(points_list)
            
        return scan_path
