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
        
        # Ghost Beam spezifische Physik-Eingabeparameter aus dem GUI
        spot_on_time_ms = kwargs.get("spot_on_time_ms", 3.0)  # Brenndauer pro Punkt
        time_delay_ms = kwargs.get("time_delay_ms", 2.0)      # Verzögerung zwischen P und S
        beam_velocity_mms = kwargs.get("beam_velocity_mms", 490.0)  # Scangeschwindigkeit der Maschine in mm/s
        
        # Transformation in mm
        hatch_spacing = hatch_spacing_um / 1000.0
        
        # Berechnung des räumlichen Abstandes nach [Lee et al., 2018] Ghost Beam-Ansatz
        # Point Spacing (Abstand zwischen zwei aufeinanderfolgenden Spots derselben Spur)
        point_spacing = (spot_on_time_ms / 1000.0) * beam_velocity_mms
        
        # Skip Spacing (Physikalische Konstante: Um wie viele Millimeter der zweite 
        # Ghost-Strahl absolut hinter dem echten Beam hinterherhinkt).
        skip_spacing = (time_delay_ms / 1000.0) * beam_velocity_mms
        
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
        
        flip_line = False
        last_y_idx = -1
        
        for idx, line in lines:
            if idx != last_y_idx and last_y_idx != -1:
                flip_line = not flip_line
            last_y_idx = idx
            
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
                
            # Temporale Wechsel-Simulation (Zeitmultiplexing auf Millisekunden-Ebene)
            for d in distances:
                # 1. Zuerst feuert der P-Strahl (Primär)
                p_pt = orig_line.interpolate(d)
                scan_path.add_segment([(p_pt.x, p_pt.y)])
                
                # 2. Direkt danach feuert der sekundäre (Ghost/verzögerte) Strahl
                if flip_line:
                    s_d = d + skip_spacing # Da d von Groß nach Klein wandert, ist Zuwachs gleichzusetzen mit Lag
                    if s_d <= length:
                        s_pt = orig_line.interpolate(s_d)
                        scan_path.add_segment([(s_pt.x, s_pt.y)])
                else:
                    s_d = d - skip_spacing
                    # Der Ghost Beam wird nur generiert, wenn er nicht schon "aus dem Material gefallen" ist (kleiner 0)
                    if s_d >= 0:
                        s_pt = orig_line.interpolate(s_d)
                        scan_path.add_segment([(s_pt.x, s_pt.y)])
            
        return scan_path
