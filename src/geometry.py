import numpy as np
from shapely.geometry import Polygon
from typing import List

class GeometryEngine:
    """
    Geometrie-Motor, der die parametrischen Basis-Objekte erstellt
    ohne ein physisches 3D-Modell slicen zu müssen (2.5D Ansatz).
    """

    @staticmethod
    def create_cube_layers(width: float, depth: float, height: float, layer_thickness_um: float) -> List[Polygon]:
        """
        Generiert iterativ eine Liste von 2D-Polygonen.
        Jedes Polygon repräsentiert eine physische Schicht in Z-Richtung, für ein Bauteil  
        mit dem Ursprung (0,0) (Zentrum der Arcam S12 Pro-Beam Bauplatte).
        
        :param width: Würfel-Dimension auf der X-Achse (in mm)
        :param depth: Würfel-Dimension auf der Y-Achse (in mm)
        :param height: Maximale Z-Höhe des Quaders (in mm)
        :param layer_thickness_um: Gewünschte Pulver-Schichtdicke pro Layer in Mikrometern (µm) (z.B. 50 µm)
        :return: Python Liste von mathematischen "Shapely Polygons"
        """
        
        # Umrechnung der Schichtdicke ins Systemmaß (mm)
        layer_thickness_mm = layer_thickness_um / 1000.0
        
        # Sicherheitsabbruch bei unmöglichen Schichtdicken (Division durch 0)
        if layer_thickness_mm <= 0:
            raise ValueError("layer_thickness_um (Schichtdicke) muss größer als 0 sein.")
            
        # Z-Slice Anzahl runden
        num_layers = int(np.ceil(height / layer_thickness_mm))
        
        # Definition der Grund-Koordinaten für den Würfel-Base-Layer. 
        # (Um den Mittelpunkt auf der Arcam Plattform auszurichten, 
        # nutzen wir Minus und Plus die halbe Länge/Breite)
        min_x = -width / 2.0
        max_x = width / 2.0
        min_y = -depth / 2.0
        max_y = depth / 2.0
        
        # Punktematrix (im Uhrzeigersinn angeordnet, um ein quadratisches Rechteck zu bilden)
        coords = [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            # Der Rand schließt sich wieder am Startpunkt
            (min_x, min_y)
        ]
        
        # Umwandlung des Punkt-Arrays in ein stabiles Shapely-Polygon
        base_polygon = Polygon(coords)
        
        # Da wir mit rein geraden extrudierten Modellen ("2.5D") arbeiten,
        # ist die Schichtgeometrie für alle Z-Schichten immer identisch.
        # Wir duplizieren das Basispolygon n-mal für jeden generierten Layer.
        return [base_polygon for _ in range(num_layers)]
