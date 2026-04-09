import os
import re
import glob
import zipfile
import tempfile

import numpy as np
import streamlit as st
from shapely.geometry import MultiPoint

from src.parser import B99Parser
from src.exporter import B99Exporter
from src.reorder import reorder_points
from src.visualization import Visualizer
from src.schema_diagrams import SchemaDiagrams
from src.thermal import MATERIALS


# ---------------------------------------------------------------------------
# Datei-Klassifikation
# ---------------------------------------------------------------------------

def classify_b99(filename: str) -> str:
    """
    Klassifiziert eine B99-Datei anhand der vorletzten Ziffer vor .B99.

    Regeln (aus Arcam-Namenskonvention):
      - vorletzte Ziffer gerade  → 'infill_even'
      - vorletzte Ziffer == 9    → 'infill_9'
      - vorletzte Ziffer ungerade (außer 9) → 'contour'
      - sonst                    → 'other'
    """
    name = os.path.splitext(filename)[0]
    if len(name) < 2:
        return 'other'
    second_last = name[-2]
    if not second_last.isdigit():
        return 'other'
    digit = int(second_last)
    if digit % 2 == 0:
        return 'infill_even'
    elif digit == 9:
        return 'infill_9'
    return 'contour'


def extract_layer_number(filename: str) -> int:
    """Extrahiert die führende Schichtnummer aus dem Dateinamen."""
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(\d+)', name)
    return int(match.group(1)) if match else 0


def find_infill_cutoff(b99_files: list) -> int:
    """
    Findet die erste Schichtnummer, in der eine Infill-Datei mit gerader
    vorletzter Ziffer vorkommt. Alle Schichten davor = Stützstruktur.
    """
    for f in sorted(b99_files):
        if classify_b99(os.path.basename(f)) == 'infill_even':
            return extract_layer_number(os.path.basename(f))
    return 2 ** 31  # Kein Infill gefunden


# ---------------------------------------------------------------------------
# Strategie-UI (zweistufig)
# ---------------------------------------------------------------------------

def render_strategy_ui() -> dict:
    """
    Rendert die Sidebar-UI für das Zwei-Stufen-Modell und gibt ein params-Dict zurück.
    """
    st.header("Strategie-Konfiguration")

    # === STUFE 1: MAKRO-SEGMENTIERUNG ===
    st.subheader("Stufe 1: Segmentierung")
    segmentation = st.selectbox(
        "Fläche aufteilen in:",
        ["Keine Segmentierung", "Schachbrett (Island)", "Streifen (Stripe)",
         "Hexagonal", "Spiralzonen (Konzentrisch)"]
    )

    seg_size = 5.0
    seg_overlap = 100.0
    seg_order = "Schachbrett (schwarz→weiß)"

    if segmentation != "Keine Segmentierung":
        seg_size = st.number_input("Segmentgröße (mm)", min_value=1.0, value=5.0, step=0.5)
        seg_overlap = st.number_input("Segment-Overlap (µm)", min_value=0.0, value=100.0, step=10.0)
        seg_order = st.selectbox(
            "Segment-Reihenfolge:",
            ["Schachbrett (schwarz→weiß)", "Spirale (außen→innen)",
             "Spirale (innen→außen)", "Zufällig", "Sequentiell (links→rechts)"]
        )

    # === STUFE 2: MIKRO-STRATEGIE ===
    st.subheader("Stufe 2: Scan-Strategie (innerhalb der Segmente)")
    micro_strategy = st.selectbox(
        "Punkte-Sortierung:",
        ["Raster (Zick-Zack)", "Spot Consecutive", "Spot Ordered",
         "Ghost Beam", "Hilbert-Kurve", "Spiral", "Peano-Kurve"]
    )

    hatch_spacing = st.number_input("Linien-Abstand / Hatch (µm)", min_value=10.0, value=200.0, step=10.0)
    rotation_angle = st.number_input(
        "Rotationswinkel pro Schicht (°)", min_value=0.0, max_value=360.0, value=67.0, step=1.0
    )

    # Strategie-spezifische Parameter
    ghost_lag = 1000.0
    spot_skip = 2
    hilbert_order = 4
    spiral_dir = "inward"

    if micro_strategy == "Ghost Beam":
        ghost_lag = st.number_input("Secondary Beam Lag (µm)", min_value=10.0, value=1000.0, step=100.0)
    if micro_strategy == "Spot Ordered":
        spot_skip = st.number_input("Skip Offset", value=2, step=1)
    if micro_strategy in ("Hilbert-Kurve", "Peano-Kurve"):
        hilbert_order = st.slider("Ordnung (Detailgrad)", 2, 7, 4)
    if micro_strategy == "Spiral":
        spiral_dir = st.radio("Richtung", ["inward", "outward"])

    # Punktabstand ist hardcoded (kommt aus dem Slicer, wird nie geändert)
    # point_spacing = 100.0 µm

    return {
        'segmentation': segmentation,
        'seg_size': seg_size,
        'seg_overlap': seg_overlap,
        'seg_order': seg_order,
        'micro_strategy': micro_strategy,
        'hatch_spacing': hatch_spacing,
        'rotation_angle_deg': rotation_angle,
        'ghost_lag': ghost_lag,
        'spot_skip': spot_skip,
        'hilbert_order': hilbert_order,
        'spiral_direction': spiral_dir,
        'point_spacing': 100.0,  # fix
    }


# ---------------------------------------------------------------------------
# Verarbeitungslogik
# ---------------------------------------------------------------------------

def process_single_infill(filepath: str, params: dict, layer_idx: int):
    """
    Liest eine Infill-B99-Datei, ordnet die Punkte neu und überschreibt die Datei.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    header_lines, points_mm = B99Parser.extract_points_and_header(content)

    if len(points_mm) == 0:
        return  # Leere Datei – unverändert lassen

    reordered = reorder_points(points_mm, params, layer_idx)
    new_content = B99Exporter.write_reordered_b99(header_lines, reordered)

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(new_content)


# ---------------------------------------------------------------------------
# Visualisierung
# ---------------------------------------------------------------------------

def _show_preview(filepath: str, params: dict, layer_idx: int, reordered: bool,
                  show_heatmap: bool, material_name: str, t_point_us: float):
    """Liest eine B99 und zeigt einen groben Plot."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    _, points_mm = B99Parser.extract_points_and_header(content)
    if len(points_mm) == 0:
        st.warning("Keine Punkte in der ausgewählten Datei gefunden.")
        return

    if reordered:
        points_mm = reorder_points(points_mm, params, layer_idx)

    polygon = MultiPoint(points_mm).convex_hull
    fig = Visualizer.plot_layer_coarse(
        polygon, points_mm, params,
        layer_index=layer_idx,
        show_heatmap=show_heatmap,
        material_name=material_name,
        t_point_us=t_point_us,
    )
    st.plotly_chart(fig, on_select="ignore")


# ---------------------------------------------------------------------------
# Haupt-App
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="EBM Strategy Converter", layout="wide")
    st.title("EBM Scan-Strategie Converter")
    st.markdown(
        "Lädt ein Baujob-ZIP-Archiv, identifiziert Infill-B99-Dateien, "
        "sortiert deren Punkte nach der gewählten Strategie neu und "
        "erzeugt ein druckfertiges ZIP."
    )

    # Sidebar: Strategie-Konfiguration
    with st.sidebar:
        params = render_strategy_ui()

        st.markdown("---")
        st.subheader("Ausgabe")
        output_dir = st.text_input(
            "Ausgabe-Ordner für ZIP",
            value=os.path.join(os.path.expanduser("~"), "EBM_Output")
        )

    # --- Datei-Upload ---
    uploaded_zip = st.file_uploader("Baujob ZIP-Archiv hochladen", type=["zip"])
    if uploaded_zip is None:
        st.info("Bitte ein ZIP-Archiv mit 'Figure Files/' Ordner hochladen.")
        return

    # --- ZIP entpacken und analysieren ---
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "input.zip")
        with open(zip_path, 'wb') as f:
            f.write(uploaded_zip.getvalue())

        extract_dir = os.path.join(tmpdir, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Figure Files Ordner suchen
        figure_dir = None
        for root, dirs, files in os.walk(extract_dir):
            if "Figure Files" in dirs:
                figure_dir = os.path.join(root, "Figure Files")
                break
            if os.path.basename(root) == "Figure Files":
                figure_dir = root
                break

        if figure_dir is None:
            st.error("Kein 'Figure Files' Ordner im ZIP gefunden!")
            return

        # B99-Dateien finden
        b99_files = sorted(glob.glob(os.path.join(figure_dir, "*.[Bb]99")))
        if not b99_files:
            st.error("Keine B99-Dateien im 'Figure Files' Ordner gefunden.")
            return

        cutoff_layer = find_infill_cutoff(b99_files)

        infill_files = []
        support_count = 0
        contour_count = 0
        for f in b99_files:
            fname = os.path.basename(f)
            cls = classify_b99(fname)
            layer = extract_layer_number(fname)
            if layer < cutoff_layer:
                support_count += 1
                continue
            if cls in ('infill_even', 'infill_9'):
                infill_files.append((f, layer))
            else:
                contour_count += 1

        col1, col2, col3 = st.columns(3)
        col1.metric("B99-Dateien gesamt", len(b99_files))
        col2.metric(f"Infill-Dateien (ab Schicht {cutoff_layer})", len(infill_files))
        col3.metric("Kontur / Stützstruktur", contour_count + support_count)

        if not infill_files:
            st.warning("Keine Infill-Dateien gefunden.")
            return

        # --- Vorschau ---
        st.markdown("---")
        st.subheader("Vorschau")

        infill_names = [os.path.basename(f) for f, _ in infill_files]
        preview_name = st.selectbox("Datei für Vorschau auswählen:", infill_names)
        preview_idx = infill_names.index(preview_name)
        preview_path, preview_layer = infill_files[preview_idx]

        col_orig, col_new = st.columns(2)
        with col_orig:
            st.markdown("**Original (aus Slicer)**")

        show_heatmap_prev = st.checkbox("Wärmeakkumulation in Vorschau anzeigen", value=False)
        material_name_prev = None
        t_point_us_prev = 13.0
        if show_heatmap_prev:
            material_name_prev = st.selectbox("Material", list(MATERIALS.keys()), key="mat_prev")
            t_point_us_prev = st.number_input("Punkthaltezeit (µs)", value=13.0, step=1.0, key="t_prev")

        _show_preview(preview_path, params, preview_layer, reordered=False,
                      show_heatmap=show_heatmap_prev, material_name=material_name_prev,
                      t_point_us=t_point_us_prev)

        # Schema-Diagramme
        with st.expander("Schema: Segmentierung (Stufe 1)"):
            seg = params['segmentation']
            if seg == 'Keine Segmentierung':
                st.components.v1.html(SchemaDiagrams.get_seg_none(), height=220)
            elif 'Schachbrett' in seg:
                st.components.v1.html(SchemaDiagrams.get_seg_chessboard(), height=220)
            elif 'Streifen' in seg:
                st.components.v1.html(SchemaDiagrams.get_seg_stripes(), height=220)
            elif 'Hexagonal' in seg:
                st.components.v1.html(SchemaDiagrams.get_seg_hexagonal(), height=220)
            elif 'Spiralzonen' in seg:
                st.components.v1.html(SchemaDiagrams.get_seg_spiral_zones(), height=220)

        with st.expander("Schema: Mikro-Scan-Strategie (Stufe 2)"):
            ms = params['micro_strategy']
            if 'Raster' in ms:
                st.components.v1.html(SchemaDiagrams.get_raster(), height=220)
            elif ms == 'Spot Consecutive':
                st.components.v1.html(SchemaDiagrams.get_spot_consecutive(), height=220)
            elif ms == 'Spot Ordered':
                st.components.v1.html(SchemaDiagrams.get_spot_ordered(), height=220)
            elif ms == 'Ghost Beam':
                st.components.v1.html(SchemaDiagrams.get_ghost_beam(), height=220)
            elif ms == 'Hilbert-Kurve':
                st.components.v1.html(SchemaDiagrams.get_hilbert(), height=220)
            elif ms == 'Spiral':
                st.components.v1.html(SchemaDiagrams.get_spiral(), height=220)
            elif ms == 'Peano-Kurve':
                st.components.v1.html(SchemaDiagrams.get_raster(), height=220)  # Fallback

        # --- Batch-Verarbeitung ---
        st.markdown("---")
        if st.button("Strategie anwenden & neues ZIP erstellen", type="primary"):
            progress = st.progress(0)
            errors = []

            for i, (filepath, layer) in enumerate(infill_files):
                try:
                    process_single_infill(filepath, params, layer)
                except Exception as e:
                    errors.append(f"{os.path.basename(filepath)}: {e}")
                progress.progress((i + 1) / len(infill_files))

            # Ausgabe-ZIP erstellen
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(uploaded_zip.name)[0]
            out_zip_name = base_name + "_NEW.zip"
            out_zip_path = os.path.join(output_dir, out_zip_name)

            with zipfile.ZipFile(out_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        arc_name = os.path.relpath(abs_path, extract_dir)
                        zf.write(abs_path, arc_name)

            if errors:
                st.warning(f"{len(errors)} Fehler beim Verarbeiten:")
                for err in errors:
                    st.text(err)

            ok_count = len(infill_files) - len(errors)
            st.success(f"{ok_count} Infill-Dateien erfolgreich konvertiert → {out_zip_path}")

            with open(out_zip_path, 'rb') as f:
                st.download_button(
                    "Download neues ZIP",
                    f.read(),
                    file_name=out_zip_name,
                    mime="application/zip"
                )

            # Vorschau nach Verarbeitung (dieselbe Datei, jetzt schon überschrieben)
            st.subheader("Vorschau nach Neuanordnung")
            _show_preview(preview_path, params, preview_layer, reordered=False,
                          show_heatmap=show_heatmap_prev, material_name=material_name_prev,
                          t_point_us=t_point_us_prev)


if __name__ == "__main__":
    main()
