import streamlit as st
import io
import zipfile
from src.geometry import GeometryEngine
from src.parser import B99Parser
from src.exporter import B99Exporter
from src.strategies.raster import RasterStrategy
from src.strategies.contour import ContourStrategy
from src.strategies.spot_consecutive import SpotConsecutiveStrategy
from src.strategies.spot_ordered import SpotOrderedStrategy
from src.strategies.ghost_beam import GhostBeamStrategy
from src.visualization import Visualizer
from src.strategies.base_strategy import ScanPath

def render_strategy_ui():
    """
    Rendert die Sidebar-UI-Komponenten für Globale Strategie-Parameter und 
    die Auswahl der Strategie-Bundles (Composite).
    Wird in beiden Modi (Generator und Converter) wiederverwendet.
    """
    st.subheader("Globale Strategie-Parameter")
    # Maschinen-Physik und Belichtungsabstände (Hatching)
    point_spacing = st.number_input("Punkt-Abstand (µm)", min_value=10.0, value=100.0, step=10.0)
    hatch_spacing = st.number_input("Linien-Abstand (Hatch) (µm)", min_value=10.0, value=200.0, step=10.0)
    # Rotation des Infill-Musters pro Z-Schicht (Normalerweise 67°)
    rotation_angle_deg = st.number_input("Rotationswinkel pro Schicht (°)", min_value=0.0, max_value=360.0, value=67.0, step=1.0)
    
    st.subheader("Strategie-Auswahl (Layer Composite)")
    # Erfordert Streamlit Multiselect für das Kombinieren (z.B. Contour + Hatching)
    strategies = st.multiselect("Strategien auswählen (Anwendung in gewählter Reihenfolge):", 
                                ["Contour", "Raster", "Spot Consecutive", "Spot Ordered", "Ghost Beam"],
                                default=["Contour", "Raster"])
                                
    with st.expander("ℹ️ Erklärungen zu den Scan-Strategien"):
        st.markdown('''
        - **Contour:** Fährt exakt die äußere Randkontur (Perimeter) des Polygons ab. Sorgt für eine glatte Seiten-Oberfläche.
        - **Raster:** Zieht klassische, durchgehende Schlangenlinien (Hatching) über die Innenfläche. Standard-Infill in der additiven Fertigung.
        - **Spot Consecutive:** Der Infill wird nicht als Linie gezogen, sondern als Reihe dicht aneinander gereihter, punktförmiger Schmelz-Dots.
        - **Spot Ordered:** Setzt Punkte, lässt aber bewusst Lücken (z.B. 2 Spots abstand), die erst in einem zweiten Durchlauf gefüllt werden. Verhindert lokale Hitze-Akkumulation sehr effektiv!
        - **Ghost Beam:** Täuscht eine Strahlteilung vor. Die Maschine springt extrem schnell zwischen einem Primär-Schmelzpunkt und einem nachziehenden Koordinaten-Punkt (Secondary Beam Lag) hin und her, um den thermischen Gradienten zu glätten.
        ''')
                                
    # Spezifische Eingabefelder werden dynamisch eingeblendet, falls die zugehörige komplexe Strategie aktiviert ist.
    ghost_skip_spacing_um = 1000.0
    if "Ghost Beam" in strategies:
        st.markdown("**Ghost Beam (Split Beam) Parameter**")
        ghost_skip_spacing_um = st.number_input("Secondary Beam Lag (Abstand des Ghostbeams in µm)", min_value=10.0, value=1000.0, step=100.0)
            
    spot_pass_skip = 2
    if "Spot Ordered" in strategies:
        st.markdown("**Spot Ordered (Multipass) Parameter**")
        spot_pass_skip = st.number_input("Skip Offset = Verpass-Abstand (z.B. +2 Spots)", value=2, step=1)
        
    # Parameter-Dict für spätere Berechnungen zusammenstellen
    return {
        'point_spacing': point_spacing,
        'hatch_spacing': hatch_spacing,
        'rotation_angle_deg': rotation_angle_deg,
        'strategies': strategies,
        'ghost_skip_spacing_um': ghost_skip_spacing_um,
        'spot_pass_skip': spot_pass_skip
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
    
    # Nutzer wählt Schicht (0 - Max), falls mehr als 1 Layer existiert.
    if len(layers) == 1:
        layer_idx = 0
        st.info("Diese Datei enthält genau 1 extrahierbare Z-Ebene (Layer).")
    else:
        layer_idx = st.slider("Wählen Sie die Z-Ebene aus", 0, len(layers) - 1, 0)
        
    # Beziehe Shapely Polygon aus Generator/Parser Array
    selected_layer_poly = layers[layer_idx]
    
    # Multipliziere Schicht mit Grund-Rotationswinkel und modulo 360 (z.B. 0°, 67°, 134° ...)
    layer_rotation = (layer_idx * params['rotation_angle_deg']) % 360.0
    
    combined_path = ScanPath(segments=[])
    selected_strategies = params['strategies']
    
    # Composite-Abhandlung: Wendet alle in Multiselect gewählten Strategien nacheinander an
    if "Contour" in selected_strategies:
        combined_path.segments.extend(ContourStrategy().generate_path(
            selected_layer_poly, point_spacing=params['point_spacing']).segments)
            
    if "Raster" in selected_strategies:
        combined_path.segments.extend(RasterStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation).segments)
            
    if "Spot Consecutive" in selected_strategies:
        combined_path.segments.extend(SpotConsecutiveStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation).segments)
            
    if "Spot Ordered" in selected_strategies:
        combined_path.segments.extend(SpotOrderedStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], 
            point_spacing=params['point_spacing'], rotation_angle_deg=layer_rotation,
            skip_offset=params['spot_pass_skip']).segments)
            
    if "Ghost Beam" in selected_strategies:
        combined_path.segments.extend(GhostBeamStrategy().generate_path(
            selected_layer_poly, hatch_spacing=params['hatch_spacing'], point_spacing=params['point_spacing'],
            rotation_angle_deg=layer_rotation, skip_spacing_um=params['ghost_skip_spacing_um']).segments)
        
    st.markdown("#### Visualisierungs-Optionen")
    c1, c2 = st.columns(2)
    with c1:
        color_by_order = st.checkbox("Scan-Reihenfolge farblich markieren (Start -> Ende)", value=True)
    with c2:
        show_arrows = st.checkbox("Strahl-Richtungspfeile einblenden (Warnung: langsamer bei vielen Segmenten)", value=False)

    fig = Visualizer.plot_layer(selected_layer_poly, combined_path, layer_index=layer_idx, color_by_order=color_by_order, show_arrows=show_arrows)
    st.plotly_chart(fig, on_select="ignore")
    
    st.markdown("---")
    
    # Massen-Export der B99
    if st.button("Generate .B99 Files (Als ZIP-Archiv exportieren)"):
        # Initialisiere ein virtuelles ZIP-File im Arbeitsspeicher
        zip_buffer = io.BytesIO()
        
        # Fortschritts-Spinner einblenden, während der Server rechnet
        with st.spinner("Berechne Scan-Algorithmen und verpacke ZIP-Archiv..."):
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for l_idx, poly in enumerate(layers):
                    l_rot = (l_idx * params['rotation_angle_deg']) % 360.0
                    layer_path = ScanPath(segments=[])
                    
                    # Hier arbeiten die Algorithmen voll im Batch-Betrieb (bis zu 400 Schichten)
                    if "Contour" in selected_strategies:
                        layer_path.segments.extend(ContourStrategy().generate_path(
                            poly, point_spacing=params['point_spacing']).segments)
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
                    
                    # Generiere den Code für GENAU DIESEN einen Layer
                    b99_string = B99Exporter.generate_b99_single_layer(layer_path, l_idx)
                    
                    if b99_string:
                        # Füge die generierte Schicht als einzelne Datei ins Archiv ein
                        zip_file.writestr(f"Layer_{l_idx:04d}.B99", b99_string)
            
        st.success("ZIP-Archiv erfolgreich formatiert!")
        # Der Browser initiiert via Text-Streamlit-Button einen ZIP Download
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
        width = st.number_input("Breite X (mm)", min_value=1.0, value=20.0)
        depth = st.number_input("Tiefe Y (mm)", min_value=1.0, value=20.0)
        height = st.number_input("Z-Höhe max (mm)", min_value=1.0, value=20.0)
        layer_thickness_um = st.number_input("Feinheit (Layer-Thickness in µm)", min_value=10.0, value=50.0, step=10.0)
        
    with col2:
        params = render_strategy_ui()

    if st.button("Geometrie & Toolpath Engine starten"):
        # Erstelle mathematische Shapely Polygone. Gibt z.B. 400 Arrays zurück (20mm / 50µm)
        layers = GeometryEngine.create_cube_layers(width, depth, height, layer_thickness_um)
        st.success(f"{len(layers)} Z-Schichten erfolgreich abgetastet!")
        # Session State rettet die generierten Daten, falls der Streamlit-Nutzer Slider bewegt (Rerendering)
        st.session_state['layers'] = layers
        st.session_state['strategy_params'] = params

    # Aufruf der Visualisierungs-Engine weiter unten
    process_and_display_layers()


def converter_mode():
    """
    Der Reverse-Engineering-UI-Modus für eingelesene Fremd-Dateien aus Arcam Systemen.
    """
    st.header(".B99 Strategy Converter (Parser & Overwrite)")
    st.markdown("Lade eine existierende `.B99` Datei eines Kollegen hoch. Extrahiere die Begrenzungsfläche des alten Teils und wende komplett neue Belichtungs-Strategien darauf an!")
    
    uploaded_file = st.file_uploader("Upload .B99 File (Arcam)", type=["B99", "b99"])
    
    params = render_strategy_ui()
    
    if uploaded_file is not None and st.button("Reverse-Engineeren & Neue Strategie anwenden"):
        # Byte-Daten aus Web konvertieren in String
        b99_content = uploaded_file.getvalue().decode("utf-8")
        with st.spinner("Lese Maschinencode aus und berechne physikalische Hüllkurven..."):
            # Der Mathematische Kern, welcher eine Punktwolke (Convex Hull) in Polygone umwandelt
            layers = B99Parser.parse_to_polygons(b99_content)
        
        st.success(f"{len(layers)} Layer-Grenzen erfolgreich aus Originaldatei extrahiert!")
        st.session_state['layers'] = layers
        st.session_state['strategy_params'] = params

    process_and_display_layers()

def main():
    # Seitenlayout in Streamlit vergrößern (Wide Mode)
    st.set_page_config(page_title="HM: EBM Strategy Software", layout="wide")
    st.title("Electron-Beam Powder Bed Fusion: Toolpath Engine")
    
    # Linke Sidebar zur App-Steuerung und Modul-Wechsel
    st.sidebar.header("Menüführung")
    mode = st.sidebar.radio("Wähle einen Modus", ["Parametric Generator", ".B99 Converter"])
    
    if mode == "Parametric Generator":
        generator_mode()
    else:
        converter_mode()

if __name__ == "__main__":
    main()
