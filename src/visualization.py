import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Polygon

class Visualizer:
    @staticmethod
    def plot_layer(polygon: Polygon, scan_path, layer_index: int = 0, color_by_order: bool = True, show_arrows: bool = False, show_heatmap: bool = False, material_name: str = None, t_point_us: float = 13.0):
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

    @staticmethod
    def plot_layer_coarse(polygon: Polygon, points_mm: np.ndarray, params: dict,
                          layer_index: int = 0, max_display_points: int = 2000,
                          show_heatmap: bool = False, material_name: str = None,
                          t_point_us: float = 13.0) -> go.Figure:
        """
        Grobe Visualisierung der reinen Punktwolke (kein ScanPath-Objekt nötig).
        Beschränkt die Darstellung auf max_display_points Punkte, um Performance
        auch bei großen Infill-Dateien zu gewährleisten.

        :param polygon:            Shapely-Polygon der Bauteilgrenze.
        :param points_mm:          np.ndarray (N, 2) – Koordinaten in mm.
        :param params:             Strategie-Parameter (für Segmentgrenzen).
        :param layer_index:        Schicht-ID für den Titel.
        :param max_display_points: Maximale Anzahl anzuzeigender Punkte.
        :param show_heatmap:       Wärmeakkumulation als Farbkodierung.
        :param material_name:      Material für Wärmeberechnung.
        :param t_point_us:         Punkthaltezeit in µs.
        :return: Plotly Figure.
        """
        fig = go.Figure()

        # 1. Bauteilgrenze (orange)
        if polygon is not None and not polygon.is_empty and polygon.geom_type == 'Polygon':
            bx, by = polygon.exterior.xy
            fig.add_trace(go.Scatter(
                x=list(bx), y=list(by),
                mode='lines',
                name='Bauteil-Grenze',
                line=dict(color='orange', width=2)
            ))

        N = len(points_mm)
        if N == 0:
            fig.update_layout(title=f"Layer {layer_index} – keine Punkte")
            return fig

        # 2. Punkte ausdünnen
        step = max(1, N // max_display_points)
        display_pts = points_mm[::step]

        # 3. Farbe: Wärme oder Scan-Reihenfolge
        if show_heatmap and material_name:
            from src.thermal import compute_heat_accumulation
            from plotly.colors import sample_colorscale
            heat = compute_heat_accumulation(points_mm, material_name, t_point_us=t_point_us)
            heat_disp = heat[::step]
            marker_color = sample_colorscale('RdYlBu_r', heat_disp.tolist())
            colorbar = dict(title="Wärme", tickvals=[0, 1], ticktext=["kalt", "heiß"])
        else:
            colors = np.arange(len(display_pts)) / max(len(display_pts) - 1, 1)
            marker_color = colors
            colorbar = dict(title="Scan-Reihenfolge", tickvals=[0, 1], ticktext=["Start", "Ende"])

        fig.add_trace(go.Scatter(
            x=display_pts[:, 0], y=display_pts[:, 1],
            mode='markers',
            name=f'Schmelzpunkte (1 von {step})',
            marker=dict(
                size=3,
                color=marker_color,
                colorscale='Viridis' if not (show_heatmap and material_name) else 'RdYlBu_r',
                colorbar=colorbar,
                showscale=True
            )
        ))

        # 4. Richtungspfeile alle ~N/20 Punkte (an den ausgedünnten Punkten)
        disp_N = len(display_pts)
        arrow_step = max(1, disp_N // 20)
        for idx in range(arrow_step, disp_N, arrow_step):
            x0, y0 = display_pts[idx - 1]
            x1, y1 = display_pts[idx]
            if (x1 - x0) ** 2 + (y1 - y0) ** 2 > 1e-6:
                fig.add_annotation(
                    x=x1, y=y1, ax=x0, ay=y0,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1.5,
                    arrowwidth=1.5, arrowcolor='rgba(100,100,200,0.7)'
                )

        # 5. Segmentgrenzen einzeichnen
        seg_type = params.get('segmentation', 'Keine Segmentierung')
        seg_size = params.get('seg_size', 5.0)
        if 'Schachbrett' in seg_type or 'Streifen' in seg_type:
            minx, maxx = points_mm[:, 0].min(), points_mm[:, 0].max()
            miny, maxy = points_mm[:, 1].min(), points_mm[:, 1].max()
            for gx in np.arange(minx, maxx, seg_size):
                fig.add_shape(type='line', x0=gx, x1=gx, y0=miny, y1=maxy,
                              line=dict(color='rgba(150,150,150,0.4)', width=1, dash='dot'))
            for gy in np.arange(miny, maxy, seg_size):
                fig.add_shape(type='line', x0=minx, x1=maxx, y0=gy, y1=gy,
                              line=dict(color='rgba(150,150,150,0.4)', width=1, dash='dot'))

        fig.update_layout(
            title=f"Layer {layer_index} – {N} Punkte (zeige jeden {step}.)",
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            showlegend=False,
            plot_bgcolor='white',
            width=800, height=700
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        return fig
