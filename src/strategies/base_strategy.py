from dataclasses import dataclass
from typing import List, Tuple, Any
from shapely.geometry import Polygon

@dataclass
class ScanPath:
    """
    Strukturierte Repräsentation eines Werkzeugpfades (Toolpath) für eine einzelne Schicht.
    Besteht aus einer Liste von Linien-Segmenten. Jedes Segment ist wiederum eine Liste von
    Koordinaten (x, y) gemessen in absoluten Millimetern (mm).
    
    Wichtig für EBM (Electron Beam Melting):
    Der physikalische Wechsel zwischen dem Ende eines Segments und dem Start des nächsten 
    führt auf der Arcam-Maschine implizit zu einem 'Beam-Off' Sprung (Jump).
    """
    segments: List[List[Tuple[float, float]]]
    
    def add_segment(self, segment: List[Tuple[float, float]]):
        """
        Fügt ein neues zusammenhängendes Belichtungs-Segment zum Pfad hinzu.
        """
        if segment:
            self.segments.append(segment)

class BaseScanStrategy:
    """
    Abstrakte Basisklasse für alle Scan-Strategien.
    Jede neue Strategie muss diese Klasse erben und die `generate_path`-Methode überschreiben.
    Dadurch stellen wir sicher, dass das System immer ein gültiges `ScanPath`-Objekt erhält, 
    welches in echte metrische Koordinaten übersetzt werden kann.
    """
    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        """
        Generiert den Belichtungspfad für ein gegebenes Polygon.
        
        :param polygon: Shapely Polygon, welches die äußere/innere Grenze des zu füllenden Bereichs darstellt
        :param kwargs: Strategie-spezifische Parameter (z.B. hatch_spacing, rotation_angle_deg, etc.)
        :return: Ein fertig formatierter ScanPath mit allen berechneten Segmenten
        """
        raise NotImplementedError("Subklassen müssen die 'generate_path' Methode zwingend implementieren")
