import streamlit as st
import io
import os
import glob
import zipfile

from src.geometry import GeometryEngine
from src.parser import B99Parser
from src.exporter import B99Exporter
from src.strategies.raster import RasterStrategy
from src.strategies.spot_consecutive import SpotConsecutiveStrategy
from src.strategies.spot_ordered import SpotOrderedStrategy
from src.strategies.ghost_beam import GhostBeamStrategy
from src.strategies.island import IslandStrategy
from src.strategies.hilbert import HilbertStrategy
from src.strategies.spiral import SpiralStrategy
from src.visualization import Visualizer
from src.strategies.base_strategy import ScanPath
from src.schema_diagrams import SchemaDiagrams
from src.thermal import MATERIALS

def render_strategy_ui():
    """
    Rendert die Sidebar-UI-Komponenten für Globale Strategie-Parameter und 
    die Auswahl der Strategie-Bundles (Composite).
    """
    st.subheader("Globale Strategie-Parameter")
    point_spacing = st.number_input("Punkt-Abstand (µm)", min_value=10.0, value=100.0, step=10.0)
    hatch_spacing = st.number_input("Linien-Abstand (Hatch) (µm)", min_value=10.0, value=200.0, step=10.0)
    rotation_angle_deg = st.number_input("Rotationswinkel pro Schicht (°)", min_value=0.0, max_value=360.0, value=67.0, step=1.0)
    
    st.subheader("Strategie-Auswahl (Layer Composite)")
    strategies = st.multiselect("Infill-Strategien auswählen (Anwendung in gewählter Reihenfolge):", 
                                ["Raster", "Spot Consecutive", "Spot Ordered", "Ghost Beam", "Island (Chessboard)", "Hilbert-Kurve", "Spiral"],
                                default=["Raster"])
                                
    with st.expander("ℹ️ Erklärungen zu den Scan-Strategien"):
        st.markdown('''
        - **Raster:** Zieht klassische, durchgehende Schlangenlinien (Hatching) über die Innenfläche. Standard-Infill in der additiven Fertigung.
        - **Spot Consecutive:** Der Infill wird nicht als Linie gezogen, sondern als Reihe dicht aneinander gereihter, punktförmiger Schmelz-Dots.
        - **Spot Ordered:** Setzt Punkte, lässt aber bewusst Lücken (z.B. 2 Spots abstand), die erst in einem zweiten Durchlauf gefüllt werden. Verhindert lokale Hitze-Akkumulation sehr effektiv!
        - **Ghost Beam:** Täuscht eine Strahlteilung vor. Die Maschine springt extrem schnell zwischen einem Primär-Schmelzpunkt und einem nachziehenden Koordinaten-Punkt (Secondary Beam Lag) hin und her, um den thermischen Gradienten zu glätten.
        - **Island (Chessboard):** Teilt die Fläche in quadratische Zonen und füllt sie im Schachbrettmuster (erst schwarze Felder, dann weiße).
        - **Hilbert-Kurve:** Raumfüllendes fraktales Linienmuster ohne scharfe 180° Wenden, das sehr gleichmäßige thermische Schmelzbäder erzeugt.
        - **Spiral:** Zieht von außen nach innen (oder umgekehrt) konzentrische Bahnen, um ebenfalls harte Umkehrpunkte zu vermeiden.
        
        *(Hinweis: Konturen werden extern vom Doktoranden berechnet und sind hier deaktiviert).*
        ''')
                                
    ghost_skip_spacing_um = 1000.0
    if "Ghost Beam" in strategies:
        st.markdown("**Ghost Beam (Split Beam) Parameter**")
        ghost_skip_spacing_um = st.number_input("Secondary Beam Lag (Abstand des Ghostbeams in µm)", min_value=10.0, value=1000.0, step=100.0)
            
    spot_pass_skip = 2
    if "Spot Ordered" in strategies:
        st.markdown("**Spot Ordered (Multipass) Parameter**")
        spot_pass_skip = st.number_input("Skip Offset = Verpass-Abstand (z.B. +2 Spots)", value=2, step=1)

    island_size_mm = 5.0
    island_overlap_um = 100.0
    if "Island (Chessboard)" in strategies:
        st.markdown("**Island (Chessboard) Parameter**")
        island_size_mm = st.number_input("Islandgröße (mm)", min_value=1.0, value=5.0, step=1.0)
        island_overlap_um = st.number_input("Island Overlap (µm)", min_value=0.0, value=100.0, step=10.0)

    hilbert_order = 4
    if "Hilbert-Kurve" in strategies:
        st.markdown("**Hilbert-Kurve Parameter**")
        hilbert_order = st.slider("Hilbert Ordnung (Detailgrad, base2)", min_value=2, max_value=7, value=4)

    spiral_direction = "inward"
    if "Spiral" in strategies:
        st.markdown("**Spiral Parameter**")
        spiral_direction = st.radio("Spiral-Richtung", ["inward", "outward"])
        
    return {
        'point_spacing': point_spacing,
        'hatch_spacing': hatch_spacing,
        'rotation_angle_deg': rotation_angle_deg,
        'strategies': strategies,
        'ghost_skip_spacing_um': ghost_skip_spacing_um,
        'spot_pass_skip': spot_pass_skip,
        'island_size_mm': island_size_mm,
        'island_overlap_um': island_overlap_um,
        'hilbert_order': hilbert_order,
        'spiral_direction': spiral_direction
    }

def process_and_display_layers():
    """
    Zentraler Verarbeitungs- und Visualisierungsblock.
    Nimmt die Polygon-Schichten entgegen, rendert via Lazy-Loading nur die im Slider aktive
    Z-Ebene (Performanzgrund) und integriert den Massen-Export (.B99).
    """
    if 'layers' not in st.session_state:
        return
        
    layers = st.session_state['layers']
    params = st.session_state['strategy_params']
    
    if len(layers) == 0:
        st.warning("Warnung: Keine gültigen geometrischen Schichten gefunden!")
        return

    st.markdown("---")
    st.subheader("Echtzeit Layer-Visualisierung (Lazy Loading)")
    
    if len(layers) == 1:
        layer_idx = 0
        st.info("Diese Datei enthält genau 1 extrahierbare Z-Ebene (Layer).")
    else:
        layer_idx = st.slider("Wählen Sie die Z-Ebene aus", 0, len(layers) - 1, 0)
        
    selected_layer_poly = layers[layer_idx]
    layer_rotation = (layer_idx * params['rotation_angle_deg']) % 360.0
    
    combined_path = ScanPath(segments=[])
    selected_strategies = params['strategies']
    
    if "Raster" in selected_strategies:
        combined_path.extend_path(RasterStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation))
            
    if "Spot Consecutive" in selected_strategies:
        combined_path.extend_path(SpotConsecutiveStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation))
            
    if "Spot Ordered" in selected_strategies:
        combined_path.extend_path(SpotOrderedStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation,
            skip_offset=params['spot_pass_skip']))
            
    if "Ghost Beam" in selected_strategies:
        combined_path.extend_path(GhostBeamStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'],
            rotation_angle_deg=layer_rotation, skip_spacing_um=params['ghost_skip_spacing_um']))

    if "Island (Chessboard)" in selected_strategies:
        combined_path.extend_path(IslandStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'],
            rotation_angle_deg=layer_rotation, island_size_mm=params['island_size_mm'], island_overlap_um=params['island_overlap_um']))

    if "Hilbert-Kurve" in selected_strategies:
        combined_path.extend_path(HilbertStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'],
            rotation_angle_deg=layer_rotation, hilbert_order=params['hilbert_order']))

    if "Spiral" in selected_strategies:
        combined_path.extend_path(SpiralStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'],
            rotation_angle_deg=layer_rotation, spiral_direction=params['spiral_direction']))
        
    st.markdown("#### Visualisierungs-Optionen")
    c1, c2 = st.columns(2)
    with c1:
        color_by_order = st.checkbox("Scan-Reihenfolge farblich markieren (Start -> Ende)", value=True)
    with c2:
        show_arrows = st.checkbox("Strahl-Richtungspfeile einblenden (Warnung: langsamer)", value=False)
        
    show_heatmap = st.checkbox("Wärmeakkumulation anzeigen (materialabhängig)")
    material_name = None
    t_point_us = 13.0
    if show_heatmap:
        material_name = st.selectbox("Material", list(MATERIALS.keys()), index=0)
        t_point_us = st.number_input("Punkthaltezeit (µs)", value=13.0, step=1.0)

    with st.spinner("Berechne Visualisierung..."):
        fig = Visualizer.plot_layer(selected_layer_poly, combined_path, layer_index=layer_idx, color_by_order=color_by_order, show_arrows=show_arrows, show_heatmap=show_heatmap, material_name=material_name, t_point_us=t_point_us)
    st.plotly_chart(fig, on_select="ignore")
    
    with st.expander("📐 Schema: Strahlverlauf"):
        if "Raster" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_raster(), height=220)
        if "Spot Consecutive" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_spot_consecutive(), height=220)
        if "Spot Ordered" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_spot_ordered(), height=220)
        if "Ghost Beam" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_ghost_beam(), height=220)
        if "Island (Chessboard)" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_island(), height=220)
        if "Hilbert-Kurve" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_hilbert(), height=220)
        if "Spiral" in selected_strategies:
            st.components.v1.html(SchemaDiagrams.get_spiral(), height=220)
            
    st.markdown("---")
    
    if st.button("Generate .B99 Files (Als ZIP-Archiv exportieren)"):
        zip_buffer = io.BytesIO()
        
        with st.spinner("Berechne Scan-Algorithmen und verpacke ZIP-Archiv..."):
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for l_idx, poly in enumerate(layers):
                    l_rot = (l_idx * params['rotation_angle_deg']) % 360.0
                    layer_path = ScanPath(segments=[])
                    
                    if "Raster" in selected_strategies:
                        layer_path.segments.extend(RasterStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot).segments)
                    if "Spot Consecutive" in selected_strategies:
                        layer_path.segments.extend(SpotConsecutiveStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot).segments)
                    if "Spot Ordered" in selected_strategies:
                        layer_path.segments.extend(SpotOrderedStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot, skip_offset=params['spot_pass_skip']).segments)
                    if "Ghost Beam" in selected_strategies:
                        layer_path.segments.extend(GhostBeamStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot, skip_spacing_um=params['ghost_skip_spacing_um']).segments)
                    if "Island (Chessboard)" in selected_strategies:
                        layer_path.segments.extend(IslandStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot, island_size_mm=params['island_size_mm'], island_overlap_um=params['island_overlap_um']).segments)
                    if "Hilbert-Kurve" in selected_strategies:
                        layer_path.segments.extend(HilbertStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot, hilbert_order=params['hilbert_order']).segments)
                    if "Spiral" in selected_strategies:
                        layer_path.segments.extend(SpiralStrategy().generate_path(
                            poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=l_rot, spiral_direction=params['spiral_direction']).segments)
                    
                    b99_string = B99Exporter.generate_b99_single_layer(layer_path, l_idx)
                    
                    if b99_string:
                        zip_file.writestr(f"Layer_{l_idx:04d}.B99", b99_string)
            
        st.success("ZIP-Archiv erfolgreich formatiert!")
        st.download_button(
            label="Download ZIP Archiv (.B99 Layer)", 
            data=zip_buffer.getvalue(), 
            file_name="Arcam_Maschinen_Toolpaths.zip", 
            mime="application/zip"
        )

def generator_mode():
    """
    UI für den Parametrischen Toolpath Generator.
    Agiert komplett ohne externe CAD(Slicing)-Files und generiert abstrakte 2.5D Polygone.
    """
    st.header("Parametric Toolpath Generator")
    st.markdown("Generiere voll parametrische 2.5D Versuchsteile (Toolpaths) ohne STL-Slicing.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Basis Geometrie-Parameter")
        width = st.number_input("Breite X (mm)", min_value=1.0, value=10.0)
        depth = st.number_input("Tiefe Y (mm)", min_value=1.0, value=10.0)
        height = st.number_input("Z-Höhe max (mm)", min_value=1.0, value=10.0)
        layer_thickness_um = st.number_input("Feinheit (Layer-Thickness in µm)", min_value=10.0, value=50.0, step=10.0)
        
    with col2:
        params = render_strategy_ui()

    if st.button("Geometrie & Toolpath Engine starten"):
        layers = GeometryEngine.create_cube_layers(width, depth, height, layer_thickness_um)
        st.success(f"{len(layers)} Z-Schichten erfolgreich abgetastet!")
        st.session_state['layers'] = layers
        st.session_state['strategy_params'] = params

    process_and_display_layers()


def converter_mode():
    st.header("B99 Batch-Converter")
    st.markdown("Lese einen Ordner mit Original-B99-Dateien ein, wende eine "
                "neue Infill-Strategie an und speichere die Ergebnisse.")
    
    col1, col2 = st.columns(2)
    with col1:
        source_dir = st.text_input("Quell-Ordner (Original B99 Dateien)", 
                                    placeholder="/pfad/zu/originalen/")
    with col2:
        target_dir = st.text_input("Ziel-Ordner (Neue Strategien)", 
                                    placeholder="/pfad/zu/output/")
    
    params = render_strategy_ui()
    
    if source_dir and os.path.exists(source_dir) and os.path.isdir(source_dir):
        b99_files = sorted(glob.glob(os.path.join(source_dir, "*.[Bb]99")))
        st.info(f"{len(b99_files)} B99-Dateien gefunden.")
        
        if b99_files:
            preview_file = st.selectbox("Vorschau-Datei auswählen", 
                                         [os.path.basename(f) for f in b99_files])
            
            if st.button("Vorschau für diese Datei laden"):
                filepath = os.path.join(source_dir, preview_file)
                content = open(filepath, 'r', encoding='utf-8').read()
                layers = B99Parser.parse_to_polygons(content)
                st.session_state['layers'] = layers
                st.session_state['strategy_params'] = params
                
    if st.button("Batch-Verarbeitung starten"):
        if not source_dir or not os.path.isdir(source_dir):
            st.error("Quell-Ordner existiert nicht!")
            return
        os.makedirs(target_dir, exist_ok=True)
        
        b99_files = sorted(glob.glob(os.path.join(source_dir, "*.[Bb]99")))
        progress = st.progress(0)
        errors = []
        
        for i, filepath in enumerate(b99_files):
            try:
                content = open(filepath, 'r', encoding='utf-8').read()
                polygons = B99Parser.parse_to_polygons(content)
                if not polygons:
                    errors.append(f"{os.path.basename(filepath)}: Keine Geometrie")
                    continue
                
                poly = polygons[0]
                layer_idx = i
                rotation = (layer_idx * params['rotation_angle_deg']) % 360.0
                
                scan_path = ScanPath(segments=[])
                selected_strategies = params['strategies']
                
                if "Raster" in selected_strategies:
                    scan_path.extend_path(RasterStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation))
                if "Spot Consecutive" in selected_strategies:
                    scan_path.extend_path(SpotConsecutiveStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation))
                if "Spot Ordered" in selected_strategies:
                    scan_path.extend_path(SpotOrderedStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation, skip_offset=params['spot_pass_skip']))
                if "Ghost Beam" in selected_strategies:
                    scan_path.extend_path(GhostBeamStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation, skip_spacing_um=params['ghost_skip_spacing_um']))
                if "Island (Chessboard)" in selected_strategies:
                    scan_path.extend_path(IslandStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation, island_size_mm=params['island_size_mm'], island_overlap_um=params['island_overlap_um']))
                if "Hilbert-Kurve" in selected_strategies:
                    scan_path.extend_path(HilbertStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation, hilbert_order=params['hilbert_order']))
                if "Spiral" in selected_strategies:
                    scan_path.extend_path(SpiralStrategy().generate_path(
                        poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'], rotation_angle_deg=rotation, spiral_direction=params['spiral_direction']))
                
                b99_out = B99Exporter.generate_b99_single_layer(scan_path, layer_idx)
                out_path = os.path.join(target_dir, os.path.basename(filepath))
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(b99_out)
                    
            except Exception as e:
                errors.append(f"{os.path.basename(filepath)}: {str(e)}")
            
            progress.progress((i + 1) / len(b99_files))
        
        st.success(f"{len(b99_files) - len(errors)} Dateien erfolgreich konvertiert!")
        if errors:
            st.warning(f"{len(errors)} Fehler:")
            for err in errors:
                st.text(err)

    if 'layers' in st.session_state:
        process_and_display_layers()


def main():
    st.set_page_config(page_title="HM: EBM Strategy Software", layout="wide")
    st.title("Electron-Beam Powder Bed Fusion: Toolpath Engine")
    
    st.sidebar.header("Menüführung")
    mode = st.sidebar.radio("Wähle einen Modus", ["Parametric Generator", ".B99 Converter"])
    
    if mode == "Parametric Generator":
        generator_mode()
    else:
        converter_mode()

if __name__ == "__main__":
    main()
