import numpy as np
from typing import Any
from shapely.geometry import Polygon, LineString
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class SpotOrderedStrategy(BaseScanStrategy):
    """
    Geordnete Spot-Melting-Strategie (Gaps).
    Anstatt einen Punkt nach dem anderen abzuarbeiten, überspringt der Elektronenstrahl
    bewusst Positionen (z.B. +2 Offset) und füllt diese Lücken in einem zweiten und dritten 
    Unterdurchgang (Sub-Pass).
    Diese Methode wurde am Oak Ridge National Laboratory wissenschaftlich erforscht,
    da sie eine thermisch homogenere Leistungsverteilung bewirkt und extrem starke
    Hitze-Hotspots verhindert. Solche Algorithmen beeinflussen den lokalen 
    Temperaturgradienten und die Erstarrungsrate maßgeblich.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        
        # Bestimmt, wie viele "Loch-Punkte" freigelassen werden. (z.B. 2 bedeutet: 1 Spot Setzen -> 2 Ignorieren)
        skip_offset = kwargs.get("skip_offset", 2)  
        
        # Ein Skip von 2 benötigt insgesamt 3 Durchgänge (Pass 0, Pass 1, Pass 2), bis die Linie voll ist.
        passes = skip_offset + 1
        hatch_spacing = hatch_spacing_um / 1000.0
        point_spacing = point_spacing_um / 1000.0
        
        scan_path = ScanPath(segments=[])
        if polygon.is_empty or hatch_spacing <= 0:
            return scan_path

        # Polygon-Horizontalisierung & Bounding Box
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        minx, miny, maxx, maxy = rotated_poly.bounds
        
        minx -= hatch_spacing
        maxx += hatch_spacing
        miny -= hatch_spacing
        maxy += hatch_spacing
        
        y_coords = np.arange(miny, maxy, hatch_spacing)
        
        lines = []
        for i, y in enumerate(y_coords):
            line = LineString([(minx, y), (maxx, y)])
            intersection = rotated_poly.intersection(line)
            
            if intersection.is_empty:
                continue
                
            geom_type = intersection.geom_type
            if geom_type == 'LineString':
                lines.append((i, intersection))
            elif geom_type == 'MultiLineString':
                for sub_line in intersection.geoms:
                    if sub_line.geom_type == 'LineString':
                        lines.append((i, sub_line))
        
        flip_line = False
        last_y_idx = -1
        
        for idx, line in lines:
            if idx != last_y_idx and last_y_idx != -1:
                flip_line = not flip_line
            last_y_idx = idx
            
            orig_line = rotate(line, rotation_angle_deg, origin=polygon.centroid, use_radians=False)
            
            length = orig_line.length
            distances = np.arange(0, length, point_spacing)
            
            points_list = []
            for d in distances:
                pt = orig_line.interpolate(d)
                points_list.append((pt.x, pt.y))
                
            if not np.isclose(length, distances[-1] if len(distances)>0 else -1):
                pt = orig_line.interpolate(length)
                points_list.append((pt.x, pt.y))
                
            if flip_line:
                points_list.reverse()
                
            # Logik für das versetzte (ordered) Setzen von Punkten, Linienweise.
            for p in range(passes):
                # Wir durchlaufen die Rasterlinie (als Punkt-Array)
                # und fügen mit dem Modulo-Operator nur jeden x-ten Punkt im aktuellen Sub-Pass an
                sub_pass_points = [points_list[i] for i in range(len(points_list)) if i % passes == p]
                
                # Zusammenfassen zu einem Linien-Segment für physikalische Weg-Visualisierung (Arrows) in Plotly
                if sub_pass_points:
                    scan_path.add_segment(sub_pass_points)
                    
        return scan_path
