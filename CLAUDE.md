# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Streamlit web app (opens at http://localhost:8501)
streamlit run app.py
```

There is no build step, test suite, or linter configured. Streamlit handles the server/client setup entirely.

## Architecture

This is a Python research tool for reordering electron beam melt (EBM) scan strategies for the Arcam S12 Pro-Beam 3D metal printer. It reads existing `.B99` point clouds from a slicer, reorders them, and outputs machine-readable `.B99` files – **without changing any coordinates**.

### Core Data Pipeline

```
ZIP upload (Figure Files/*.B99)
  → app.py: classify_b99 / find_infill_cutoff   (identify infill layers)
  → parser.py: extract_points_and_header         (header + N×2 NumPy array in mm)
  → reorder.py: reorder_points                   (Stage 1: segmentation, Stage 2: micro-sort)
  → exporter.py: write_reordered_b99             (header unchanged, new point order, \r\n)
  → ZIP with all original files, infill replaced
```

### Coordinate System

- Arcam S12 build platform: 120×120 mm, origin at center
- `.B99` files use normalized coords in [-1, +1]; scale factor is 60 (`x_mm = x_norm * 60`)
- `parser.py` scales in; `exporter.py` scales out (17 significant digits, `\r\n` line endings)

### Two-Stage Reordering (`src/reorder.py`)

**Stage 1 – Macro Segmentation** (`segment_points`): divides the point cloud into regions.
Implemented types: `_segment_chessboard`, `_segment_stripes`, `_segment_hexagonal`, `_segment_spiral_zones`.

**Stage 2 – Micro Sort** (`sort_within_segment`): sorts points within each segment.
Implemented: `sort_raster`, `sort_spot_ordered`, `sort_ghost_beam`, `sort_hilbert`, `sort_spiral`, `sort_peano`.

All functions take `np.ndarray (N, 2)` and return the same points in a new order.

### File Classification (`app.py`)

Infill files are identified by the **second-to-last digit** before `.B99`:
- Even digit → `infill_even` (reorder)
- `9` → `infill_9` (reorder, after cutoff layer)
- Odd digit → `contour` (pass through unchanged)
- All layers before the first even-digit layer → support structure (pass through)

### Thermal Analysis (`src/thermal.py`)

Gaussian heat diffusion (`exp(-d² / (4αt))`) with material-specific properties (PM HSS, IN718, Ti-6Al-4V). Returns a normalized heat index [0,1] per point for heatmap coloring in `plot_layer_coarse`.
