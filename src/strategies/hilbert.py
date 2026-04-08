import numpy as np
from typing import Any
from shapely.geometry import Polygon, LineString
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

def hilbert_d2xy(n: int, d: int) -> tuple[int, int]:
    """Konvertiert Hilbert-Index d zu (x,y) Koordinaten in n×n Grid."""
    x = y = 0
    s = 1
    while s < n:
        rx = 1 if (d & 2) else 0
        ry = 1 if ((d & 1) ^ rx) else 0
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        d //= 4
        s *= 2
    return x, y

class HilbertStrategy(BaseScanStrategy):
    """
    Hilbert-Kurve Scan-Strategie.
    Raumfüllende fraktale Kurve ohne Richtungspräferenz und ohne 180-Grad-Wendepunkte.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        hilbert_order = kwargs.get("hilbert_order", 4)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        
        point_spacing = point_spacing_um / 1000.0
        scan_path = ScanPath(segments=[])
        
        if polygon.is_empty or point_spacing <= 0:
            return scan_path
            
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        minx, miny, maxx, maxy = rotated_poly.bounds
        
        n = 2 ** hilbert_order
        total_points = n * n
        
        dx = (maxx - minx) / n
        dy = (maxy - miny) / n
        
        # Generiere Hilbert Pfad in der Bounding Box
        h_points = []
        for d in range(total_points):
            gx, gy = hilbert_d2xy(n, d)
            real_x = minx + gx * dx + dx/2
            real_y = miny + gy * dy + dy/2
            h_points.append((real_x, real_y))
            
        # Wir bilden eine LineString durch alle berechneten Punkte
        h_line = LineString(h_points)
        
        # Clippen an der Polygon-Grenze
        intersection = rotated_poly.intersection(h_line)
        
        lines = []
        if intersection.is_empty:
            pass
        elif intersection.geom_type == 'LineString':
            lines.append(intersection)
        elif intersection.geom_type == 'MultiLineString':
            for line in intersection.geoms:
                if line.geom_type == 'LineString':
                    lines.append(line)
                    
        # Rotiere und discretize 
        for line in lines:
            orig_line = rotate(line, rotation_angle_deg, origin=polygon.centroid, use_radians=False)
            length = orig_line.length
            distances = np.arange(0, length, point_spacing)
            
            pts = []
            for d in distances:
                pt = orig_line.interpolate(d)
                pts.append((pt.x, pt.y))
                
            if not np.isclose(length, distances[-1] if len(distances)>0 else -1):
                pt = orig_line.interpolate(length)
                pts.append((pt.x, pt.y))
                
            if pts:
                scan_path.add_segment(pts)
                
        return scan_path
