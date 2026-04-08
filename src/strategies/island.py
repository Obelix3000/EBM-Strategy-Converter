import numpy as np
from typing import Any
from shapely.geometry import Polygon, box, LineString
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath
from src.strategies.raster import RasterStrategy

class IslandStrategy(BaseScanStrategy):
    """
    Island (Chessboard) Scan-Strategie.
    Teilt die Schicht in ein Schachbrettmuster quadratischer Zellen (Islands) auf.
    Die Zellen werden phasenweise belichtet (erst "schwarz", dann "weiß"), 
    was zu einem großen lokalen Abstand zwischen zeitlich direkt aufeinanderfolgenden
    Scans führt und den Verzug minimiert.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        island_size_mm = kwargs.get("island_size_mm", 5.0)
        island_overlap_um = kwargs.get("island_overlap_um", 100.0)
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        
        scan_path = ScanPath(segments=[])
        if polygon.is_empty or island_size_mm <= 0:
            return scan_path
            
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        minx, miny, maxx, maxy = rotated_poly.bounds
        
        overlap_mm = island_overlap_um / 1000.0
        step = island_size_mm
        
        cells = []
        for row, y in enumerate(np.arange(miny, maxy, step)):
            for col, x in enumerate(np.arange(minx, maxx, step)):
                cell_box = box(x - overlap_mm/2, y - overlap_mm/2,
                               x + island_size_mm + overlap_mm/2,
                               y + island_size_mm + overlap_mm/2)
                cells.append((row, col, cell_box))
                
        # Schachbrett-Aufteilung (erst alle "schwarzen", dann "weißen" Felder)
        phase1 = [(r, c, b) for r, c, b in cells if (r + c) % 2 == 0]
        phase2 = [(r, c, b) for r, c, b in cells if (r + c) % 2 == 1]
        ordered_cells = phase1 + phase2
        
        raster_gen = RasterStrategy()
        
        for r, c, cell_box in ordered_cells:
            cell_clipped = rotated_poly.intersection(cell_box)
            if cell_clipped.is_empty:
                continue
                
            cell_path = raster_gen.generate_path(
                cell_clipped, 
                hatch_spacing=hatch_spacing_um, 
                point_spacing=point_spacing_um, 
                rotation_angle_deg=0.0
            )
            
            for segment in cell_path.segments:
                if len(segment) < 2:
                    continue
                orig_line = rotate(LineString(segment), rotation_angle_deg, origin=polygon.centroid, use_radians=False)
                scan_path.add_segment([(pt[0], pt[1]) for pt in orig_line.coords])
                
        return scan_path
