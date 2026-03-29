import plotly.graph_objects as go
from shapely.geometry import Polygon
from src.strategies.base_strategy import ScanPath

class Visualizer:
    @staticmethod
    def plot_layer(polygon: Polygon, scan_path: ScanPath, layer_index: int = 0):
        """
        Plottet eine 2.5D Einzel-Schicht samt ihrer Grenzgeometrie (Boundary Polygon) 
        und den generierten Scan-Pfaden (Toolpaths) als interagierbare Plotly-Figure.
        Dies ermoeglicht in der Web-UI "Hineinzoomen" und Hovern, um Fehler in den
        Algorithmen sofort sichten zu können.
        
        :param polygon: Das Shapely-Base-Polygon, das die Ränder abbildet.
        :param scan_path: Der Path mit allen gerenderten Schmelz-Segmenten (Toolpath).
        :param layer_index: Eine ID fuer den Plotly Title.
        :return: Ein fertig konfiguriertes Plotly Graph-Objekt.
        """
        fig = go.Figure()

        # 1. Hinzufügen der Außengrenzen (Bounding Box / Perimeter)
        if polygon is not None and not polygon.is_empty:
            x, y = polygon.exterior.xy
            # Linie in Plotly als Oranger Strich
            fig.add_trace(go.Scatter(x=list(x), y=list(y),
                                     mode='lines',
                                     name='Layer Boundary',
                                     line=dict(color='orange', width=2)))

            # Falls das abgetastete Polygon noch interne Löcher hat (z.B. Test-Infill)
            for i, interior in enumerate(polygon.interiors):
                xi, yi = interior.xy
                fig.add_trace(go.Scatter(x=list(xi), y=list(yi),
                                         mode='lines',
                                         name=f'Hole {i}',
                                         line=dict(color='orange', width=2)))

        # 2. Hinzufügen der Strategie-Scan-Pfade (Raster, Spots, etc)
        if scan_path is not None:
            # Für jedes separate physikalische Jump-Segment im ScanPath:
            for j, segment in enumerate(scan_path.segments):
                xs = [pt[0] for pt in segment]
                ys = [pt[1] for pt in segment]
                # Modus 'lines+markers' visualisiert sowohl die verbundene Beam-Bahn als auch die eigentlichen
                # diskreten Aufpunkte (Schmelz-Pulses).
                fig.add_trace(go.Scatter(x=xs, y=ys,
                                         mode='lines+markers',
                                         name=f'Segment {j}',
                                         marker=dict(size=4, color='rgba(0,0,255,0.7)'),
                                         line=dict(color='rgba(0,0,255,0.4)', width=1)))

        # 3. Layout konfigurieren, Metrisches Gitternetz anzeigen
        fig.update_layout(title=f"Layer {layer_index} Toolpath",
                          xaxis_title="X (mm)",
                          yaxis_title="Y (mm)",
                          # Quadratische Proportionalität erzwingen, damit Geometrien nicht verzerren! (scaleratio = 1)
                          xaxis=dict(scaleanchor="y", scaleratio=1), 
                          showlegend=False,
                          plot_bgcolor='white',
                          width=800, height=800)
        
        # Ein zartes Graues Raster im Hintergrund dient der Skalierungs-Darstellung (1mm Grid)
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig
