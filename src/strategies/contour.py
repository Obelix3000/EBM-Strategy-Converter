import numpy as np
from typing import Any
from shapely.geometry import Polygon, LineString
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class ContourStrategy(BaseScanStrategy):
    """
    Abfahren der äußeren Kontur des Polygons (Surface Quality Outline).
    Dient der thermischen Glättung und exakten Formgebung des Bauteils, bevor oder
    nachdem das innenliegende Infill (z.B. Raster) gedruckt wird.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        # Standardparameter für Punktabstand abrufen
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        point_spacing = point_spacing_um / 1000.0  # Konvertierung zu mm
        
        scan_path = ScanPath(segments=[])
        
        # Sicherheitsabbruch bei leeren Daten
        if polygon.is_empty or point_spacing <= 0:
            return scan_path
            
        # Extrahieren des Randpfades aus dem Shapely Polygon
        exterior_line = LineString(polygon.exterior.coords)
        length = exterior_line.length
        
        # Start bei Distanz 0 und inkrementelles Erstellen von Stützpunkten
        distances = np.arange(0, length, point_spacing)
        points_list = []
        
        for d in distances:
            pt = exterior_line.interpolate(d)
            points_list.append((pt.x, pt.y))
            
        # Garantieren, dass das Bauteil komplett von einer geschlossenen Linie umschlossen ist.
        # Fallback: Den absolut letzten Kontur-Punkt zur Liste hinzufügen.
        if distances[-1] < length:
            pt = exterior_line.interpolate(length)
            points_list.append((pt.x, pt.y))
            
        # Den gesamten Hüllen-Pfad als ein kontinuierliches Segment übergeben
        scan_path.add_segment(points_list)
        return scan_path
