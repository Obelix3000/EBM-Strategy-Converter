import plotly.graph_objects as go
from shapely.geometry import Polygon
from src.strategies.base_strategy import ScanPath

class Visualizer:
    @staticmethod
    def plot_layer(polygon: Polygon, scan_path: ScanPath, layer_index: int = 0, color_by_order: bool = True, show_arrows: bool = False):
        """
        Plottet eine 2.5D Einzel-Schicht samt ihrer Grenzgeometrie (Boundary Polygon) 
        und den generierten Scan-Pfaden (Toolpaths) als interagierbare Plotly-Figure.
        Dies ermoeglicht in der Web-UI "Hineinzoomen" und Hovern, um Fehler in den
        Algorithmen sofort sichten zu können.
        
        :param polygon: Das Shapely-Base-Polygon, das die Ränder abbildet.
        :param scan_path: Der Path mit allen gerenderten Schmelz-Segmenten (Toolpath).
        :param layer_index: Eine ID fuer den Plotly Title.
        :param color_by_order: Wenn aktiv, wird der Verlauf farblich (Viridis) kodiert.
        :param show_arrows: Wenn aktiv, werden Richtungspfeile an den Segmenten gezeichnet.
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
            num_segments = len(scan_path.segments)
            from plotly.colors import sample_colorscale
            
            # Für jedes separate physikalische Jump-Segment im ScanPath:
            for j, segment in enumerate(scan_path.segments):
                xs = [pt[0] for pt in segment]
                ys = [pt[1] for pt in segment]
                
                # Standardfarben
                marker_color = 'rgba(0,0,255,0.7)'
                line_color = 'rgba(0,0,255,0.4)'
                arrow_color = 'red'
                
                if color_by_order and num_segments > 0:
                    val = j / num_segments if num_segments > 1 else 0
                    c = sample_colorscale('Viridis', [val])[0]
                    # Passe Transparenz für Linien leicht an
                    c_line = c.replace('rgb', 'rgba').replace(')', ', 0.6)') if 'rgb(' in c else c
                    marker_color = c
                    line_color = c_line
                    arrow_color = c
                
                # Modus 'lines+markers' visualisiert sowohl die verbundene Beam-Bahn als auch die eigentlichen diskreten Aufpunkte
                fig.add_trace(go.Scatter(x=xs, y=ys,
                                         mode='lines+markers',
                                         name=f'Segment {j}',
                                         marker=dict(size=4, color=marker_color),
                                         line=dict(color=line_color, width=1)))
                                         
                # Richtungspfeile einblenden (in der Mitte jedes Segments)
                if show_arrows and len(segment) >= 2:
                    mid_idx = max(1, len(segment) // 2)
                    x_start = segment[mid_idx - 1][0]
                    y_start = segment[mid_idx - 1][1]
                    x_end = segment[mid_idx][0]
                    y_end = segment[mid_idx][1]
                    
                    # Pfeil nur zeichnen, wenn Punkte nicht identisch sind
                    if (x_end - x_start)**2 + (y_end - y_start)**2 > 1e-6:
                        fig.add_annotation(
                            x=x_end, y=y_end,
                            ax=x_start, ay=y_start,
                            xref="x", yref="y",
                            axref="x", ayref="y",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1.5,
                            arrowwidth=1.5,
                            arrowcolor=arrow_color
                        )

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
