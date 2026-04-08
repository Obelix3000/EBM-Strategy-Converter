import numpy as np
from typing import Any
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class SpiralStrategy(BaseScanStrategy):
    """
    Spiral-Scan Strategie.
    Der Strahl fährt spiralförmig von außen nach innen (oder umgekehrt).
    Minimiert Defekte an 180°-Wendepunkten im Vergleich zu Raster.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        spiral_direction = kwargs.get("spiral_direction", "inward")
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        
        hatch_spacing = hatch_spacing_um / 1000.0
        point_spacing = point_spacing_um / 1000.0
        scan_path = ScanPath(segments=[])
        
        if polygon.is_empty or hatch_spacing <= 0:
            return scan_path
            
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        
        offsets = []
        i = 0
        while True:
            offset_mm = i * hatch_spacing
            offset_poly = rotated_poly.buffer(-offset_mm)
            if offset_poly.is_empty or not offset_poly.is_valid:
                break
                
            # offset_poly kann ein Polygon oder MultiPolygon sein
            # Wir benötigen die boundaries (LineString oder MultiLineString)
            bounds = offset_poly.boundary
            if bounds.geom_type == 'LineString':
                offsets.append(bounds)
            elif bounds.geom_type == 'MultiLineString':
                for line in bounds.geoms:
                    offsets.append(line)
            i += 1
            
        if not offsets:
            return scan_path
            
        if spiral_direction == "outward":
            offsets.reverse()
            
        # Wir fügen jede Einzelkontur als Linensegment hinzu
        for line in offsets:
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
