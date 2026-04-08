import numpy as np
from typing import Any
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class GhostBeamStrategy(BaseScanStrategy):
    """
    Ghost Beam Scan-Strategie (Strahlteilung & Spurgenerierung).
    EBM-Maschinen können ihren Elektronenstrahl so schnell ablenken (Deflexion), dass sie
    quasiparallel zwei Schmelzpunkte auf der Pulverbett-Oberfläche bedienen.
    In diesem Szenario führt ein Primär-Strahl (Primary) die Schmelzfront an und ein
    Sekundär-Strahl (Ghost Beam) folgt der Route exakt hinten auf der Bahn nach, 
    um den Temperaturabfall auszugleichen und das Schmelzbad zu beruhigen.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        
        # Globale und spezifische Koordinaten-Parameter
        point_spacing_um = kwargs.get("point_spacing", 100.0) 
        skip_spacing_um = kwargs.get("skip_spacing_um", 1000.0)
        
        # Transformation in mm
        hatch_spacing = hatch_spacing_um / 1000.0
        point_spacing = point_spacing_um / 1000.0
        
        # Skip Spacing (Physikalische Konstante: Um wie viele Millimeter der zweite 
        # Ghost-Strahl (Sekundärpunkt) absolut hinter dem Primärpunkt auf der Trajektorie hinterherhinkt).
        skip_spacing = skip_spacing_um / 1000.0
        
        scan_path = ScanPath(segments=[])
        if polygon.is_empty or hatch_spacing <= 0 or point_spacing <= 0:
            return scan_path

        # Klassisches Polygon-Clipping per Rotation für parallele Linien (Raster)
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
        
        lines.sort(key=lambda item: (item[0], item[1].bounds[0]))
        
        for i, (idx, line) in enumerate(lines):
            flip_line = (i % 2 == 1)
            
            orig_line = rotate(line, rotation_angle_deg, origin=polygon.centroid, use_radians=False)
            length = orig_line.length
            
            # Punktwolken-Aufbau anhand der exakten Wegmarken
            distances = np.arange(0, length + point_spacing, point_spacing)
            if distances[-1] > length:
                distances[-1] = length
                
            if flip_line:
                # Wichtig: Der Ghost Beam liegt bei ablenkenden Strahlen trotzdem immer HINTER 
                # der primären Bewegungsrichtung! Wird die Linie gedreht, müssen die Distanzen
                # gespiegelt werden, weil der Primärstrahl jetzt am hinteren Koordinaten-Ende startet.
                distances = length - distances
                
            # Temporale Wechsel-Simulation (Raumbereichs-Multiplexing)
            for d in distances:
                # 1. Zuerst feuert der P-Strahl (Primär) als eigenes Beam-Segment
                p_pt = orig_line.interpolate(d)
                scan_path.add_segment([(p_pt.x, p_pt.y)])
                
                # 2. Danach springt (Jumps) der Strahl extrem weit zurück für den Ghost/Sekundär-Punkt
                # Damit Plotly diese Off-Beam-Jumps nicht als krasse diagonale ZickZack-Linie malt,
                # werden sie als separate, strikt unverbundene Segmente deklariert! Das verhindert auch Fehldarstellungen von Pfeilen.
                if flip_line:
                    s_d = d + skip_spacing # Da d von Groß nach Klein wandert, ist Zuwachs gleichzusetzen mit Lag
                    if s_d <= length:
                        s_pt = orig_line.interpolate(s_d)
                        scan_path.add_segment([(s_pt.x, s_pt.y)], segment_type="ghost")
                else:
                    s_d = d - skip_spacing
                    if s_d >= 0:
                        s_pt = orig_line.interpolate(s_d)
                        scan_path.add_segment([(s_pt.x, s_pt.y)], segment_type="ghost")
                
        return scan_path
