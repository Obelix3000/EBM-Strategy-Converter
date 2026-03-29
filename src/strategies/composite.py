from typing import Any, List
from shapely.geometry import Polygon
from src.strategies.base_strategy import BaseScanStrategy, ScanPath

class CompositeStrategy(BaseScanStrategy):
    """
    Wendelt das Design Pattern "Composite" an.
    Dient als Wrapper-Klasse, welche nicht nur eine, sondern eine beliebige Sequenz
    an Strategien (z.B. [ContourStrategy(), RasterStrategy()]) nacheinander auf dasselbe
    Polygon-Gebilde anwendet. Dies ist in der additiven Fertigung gängig, um beispielsweise
    erst genaue Ränder mit Contour-Pässen zu bilden, und das entstehende Loch
    mit günstigem/schnellem Infill-Raster zu füllen!
    """
    def __init__(self, strategies: List[BaseScanStrategy]):
        # Alle anzugehenden Basis-Strategien speichern
        self.strategies = strategies

    def generate_path(self, polygon: Polygon, **kwargs: Any) -> ScanPath:
        # Sammel-Container für alle gebündelten Segmente erstellen
        combined_path = ScanPath(segments=[])
        
        # Iteration über jede übergebene Unter-Strategie
        for strategy in self.strategies:
            # Polymorpher Aufruf von `generate_path` (Jede Strategy weiß selbst wie sie arbeitet)
            path = strategy.generate_path(polygon, **kwargs)
            if path and path.segments:
                # Aneinanderhängen der Listen
                combined_path.segments.extend(path.segments)
                
        return combined_path
