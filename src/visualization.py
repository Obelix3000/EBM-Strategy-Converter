import plotly.graph_objects as go
from shapely.geometry import Polygon
from src.strategies.base_strategy import ScanPath

class Visualizer:
    @staticmethod
    def plot_layer(polygon: Polygon, scan_path: ScanPath, layer_index: int = 0, color_by_order: bool = True, show_arrows: bool = False, show_heatmap: bool = False, material_name: str = None, t_point_us: float = 13.0):
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
            total_points = sum(len(seg) for seg in scan_path.segments)
            from plotly.colors import sample_colorscale
            
            global_pt_idx = 0
            
            heat_values = []
            if show_heatmap and material_name:
                import numpy as np
                from src.thermal import compute_heat_accumulation
                all_points = []
                for seg in scan_path.segments:
                    all_points.extend(seg)
                if len(all_points) > 0:
                    heat_array = compute_heat_accumulation(np.array(all_points), material_name, t_point_us=t_point_us)
                    heat_values = heat_array.tolist()

            
            # Für jedes separate physikalische Jump-Segment im ScanPath:
            for j, segment in enumerate(scan_path.segments):
                xs = [pt[0] for pt in segment]
                ys = [pt[1] for pt in segment]
                
                seg_type = scan_path.segment_types[j] if hasattr(scan_path, 'segment_types') and scan_path.segment_types else "primary"
                
                # Standardfarben
                marker_color = 'rgba(0,0,255,0.7)'
                line_color = 'rgba(0,0,255,0.4)'
                arrow_color = 'red'
                
                trace_mode = 'lines+markers'
                marker_symbol = 'circle'
                marker_size = 4
                
                if show_heatmap and heat_values:
                    segment_heat = [heat_values[global_pt_idx + i] for i in range(len(segment))]
                    marker_color = sample_colorscale('RdYlBu_r', segment_heat)
                    val_seg = sum(segment_heat) / len(segment_heat) if segment_heat else 0
                    c = sample_colorscale('RdYlBu_r', [val_seg])[0]
                    line_color = c.replace('rgb', 'rgba').replace(')', ', 0.4)') if 'rgb(' in c else c
                    arrow_color = c
                    if seg_type == "ghost":
                        marker_symbol = 'x'
                        marker_size = 6
                        trace_mode = 'markers'
                else:
                    if seg_type == "ghost":
                        marker_color = 'rgba(255, 0, 0, 1.0)'
                        line_color = 'rgba(255, 0, 0, 0.5)'
                        arrow_color = 'red'
                        marker_symbol = 'x'
                        marker_size = 6
                        trace_mode = 'markers'
                    elif color_by_order and total_points > 0:
                        vals = [(global_pt_idx + i) / total_points for i in range(len(segment))]
                        marker_color = sample_colorscale('Viridis', vals)
                        val_seg = (global_pt_idx + len(segment)/2) / total_points
                        c = sample_colorscale('Viridis', [val_seg])[0]
                        line_color = c.replace('rgb', 'rgba').replace(')', ', 0.4)') if 'rgb(' in c else c
                        arrow_color = c

                global_pt_idx += len(segment)
                
                fig.add_trace(go.Scatter(x=xs, y=ys,
                                         mode=trace_mode,
                                         name=f'Segment {j}',
                                         marker=dict(symbol=marker_symbol, size=marker_size, color=marker_color),
                                         line=dict(color=line_color, width=1)))
                                         
                # Richtungspfeile einblenden (auf komplexen Linien mehrmals)
                if show_arrows and len(segment) >= 2:
                    # Pfeile an mehreren Intervallen platzieren, max. alle N Punkte, damit man GhostBeam-Jumps sieht
                    step = max(2, len(segment) // 6)
                    for mid_idx in range(1, len(segment), step):
                        x_start = segment[mid_idx - 1][0]
                        y_start = segment[mid_idx - 1][1]
                        x_end = segment[mid_idx][0]
                        y_end = segment[mid_idx][1]
                        
                        # Pfeil nur zeichnen, wenn Punkte räumlich nicht identisch sind
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
