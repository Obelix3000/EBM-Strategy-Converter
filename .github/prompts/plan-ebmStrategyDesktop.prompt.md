## Plan: Desktop Qt + 3D Preview

Move the Streamlit UI to a PySide6 desktop app with a left 3D viewport and right settings panel, reuse the existing parse/reorder/export pipeline, add a coarse per-layer 3D preview (downsampled point cloud + optional path lines), and package a Windows EXE with PyInstaller.

**Steps**
1. Extract Streamlit-only logic into reusable core functions so the desktop UI can call them directly; keep the core pipeline unchanged by reusing `parser`, `reorder`, and `exporter` functions.
2. Implement a Qt main window with a splitter: left 3D viewport, right settings panel; wire controls to existing strategy params, file load, layer slider, and preview mode toggle (points/lines).
3. Add a render adapter that converts per-layer data to 3D preview buffers: apply downsampling, assign z = layer_index * 0.08 mm, and color by strategy/segment while keeping contour/infill flags for future toggles.
4. Integrate a 3D renderer using VisPy (OpenGL) inside Qt; draw build plate grid (120x120), boundary polygon, point cloud markers, and optional polyline for scan path; support camera controls and per-layer updates without full reinit.
5. Add background processing for reorder/export to keep UI responsive (Qt thread pool), with progress updates and caching of computed layer previews.
6. Package a Windows-only EXE with PyInstaller, bundling Qt + VisPy + numpy + shapely; update run/build instructions accordingly.

**Relevant files**
- [app.py](app.py) — reuse classification functions and current UI params mapping; split core logic out of Streamlit
- [src/parser.py](src/parser.py) — parse B99 header + points
- [src/reorder.py](src/reorder.py) — `reorder_points` pipeline, segmentation + micro-sort
- [src/exporter.py](src/exporter.py) — write reordered B99 and ZIP
- [src/visualization.py](src/visualization.py) — current downsampling logic and strategy color ideas to replicate in 3D
- [src/thermal.py](src/thermal.py) — optional heatmap color mode if needed later
- [requirements.txt](requirements.txt) — add Qt + VisPy + PyInstaller deps
- [README.md](README.md) — update run/build instructions (desktop app)

**Verification**
1. Load a sample ZIP and confirm layer list and infill/contour classification match current Streamlit output.
2. Move the layer slider and verify 3D preview updates quickly (downsampled) and z-spacing equals 0.08 mm.
3. Toggle point/line preview and ensure colors reflect strategy segmentation order.
4. Export a reordered ZIP and compare against current Streamlit output for a small sample layer.
5. Build the Windows EXE with PyInstaller and launch on a clean machine/VM.

**Decisions**
- Use PySide6 (Qt) desktop UI with VisPy for fast 3D point/line rendering.
- Preview is coarse, single-layer at a time; z derived from fixed 0.08 mm layer height.
- Windows-only packaging for now via PyInstaller.

**Further Considerations**
1. If VisPy integration proves unstable, fall back to QtWebEngine + Plotly 3D using existing plotting logic, or PyQtGraph OpenGL for simpler integration.
