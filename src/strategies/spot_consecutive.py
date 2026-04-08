import math
from typing import Any
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class SpotConsecutiveStrategy(BaseScanStrategy):
    """
    Konsekutive Spot-Melting-Strategie.
    Bewegt sich sequentiell von links nach rechts, ähnlich einem Raster-Modell.
    Das Kernelement hierbei ist: Jeder Einzelpunkt auf der Rasterlinie wird als isoliertes Segment 
    abgespeichert. Das erzwingt beim Export ins .B99 Format eine Unmenge an 
    kleinen physikalischen Sprüngen (Beam Turns On -> Spot Melt -> Beam Off -> Jump to next Spot).
    Dies verhindert den klassischen durchgehenden Wärmefluss des Lasers!
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        rotation_angle_deg = kwargs.get("rotation_angle_deg", 0.0)
        hatch_spacing_um = kwargs.get("hatch_spacing", 200.0)
        point_spacing_um = kwargs.get("point_spacing", 100.0)
        
        # Normalisierung in Millimeter
        hatch_spacing = hatch_spacing_um / 1000.0
        point_spacing = point_spacing_um / 1000.0
        
        scan_path = ScanPath(segments=[])
        
        # Abfangen von falschen/leeren Geometrien
        if polygon.is_empty or hatch_spacing <= 0:
            return scan_path

        # Rotation des gesamten Polygons, um die Rasterlinien mathematisch horizontal berechnen zu können
        rotated_poly = rotate(polygon, -rotation_angle_deg, origin='centroid', use_radians=False)
        minx, miny, maxx, maxy = rotated_poly.bounds
        
        # Sicherheits-Padding um Kanten zu überlappen
        minx -= hatch_spacing
        maxx += hatch_spacing
        miny -= hatch_spacing
        maxy += hatch_spacing
        
        # Reihe für Reihe interpolieren
        y_coords = np.arange(miny, maxy, hatch_spacing)
        
        lines = []
        for i, y in enumerate(y_coords):
            line = LineString([(minx, y), (maxx, y)])
            # Intersection beschneidet die unendliche Rasterlinie auf den echten Bauteilinnenraum
            intersection = rotated_poly.intersection(line)
            
            if intersection.is_empty:
                continue
                
            geom_type = intersection.geom_type
            if geom_type == 'LineString':
                lines.append((i, intersection))
            elif geom_type == 'MultiLineString':
                # Handhabung von Bauteilen mit Löchern/Gabelungen
                for sub_line in intersection.geoms:
                    if sub_line.geom_type == 'LineString':
                        lines.append((i, sub_line))
        
        lines.sort(key=lambda item: (item[0], item[1].bounds[0]))
        
        # Spot-Berechnungs und Rotationssequenz (Zick-Zack Umkehrung wie im standard-Raster)
        for i, (idx, line) in enumerate(lines):
            flip_line = (i % 2 == 1)
            
            # Revertierung der Rotation in das Ursprungssystem (also z.B. wieder um 67 Grad gedreht)
            orig_line = rotate(line, rotation_angle_deg, origin=polygon.centroid, use_radians=False)
            
            length = orig_line.length
            # Bestimmung der Aufpunkt-Längen (Jeder Spot ein Punktabstand)
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
                
            # Alle Punkte dieser Linie/Spotreihe als ein Segment hinzufügen
            # Das ändert nichts am B99 Output (da dieser nur ABS Punkte iteriert),
            # sorgt aber dafür, dass UI-Pfeile gezeichnet werden können und Linien logisch zusammenhängen.
            if points_list:
                scan_path.add_segment(points_list)
            
        return scan_path
