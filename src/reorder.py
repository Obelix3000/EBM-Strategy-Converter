"""
Punkt-Neuanordnung (Point Reordering) für den EBM Strategy Converter V4.

Zwei-Stufen-Ansatz:
  Stufe 1 (Makro): Segmentierung der Punktwolke in Bereiche (Schachbrett, Streifen, etc.)
  Stufe 2 (Mikro): Sortierung der Punkte innerhalb jedes Segments (Raster, Hilbert, etc.)

Wichtig: Punktpositionen werden NIEMALS verändert – nur die Reihenfolge.
"""

import numpy as np
from shapely.geometry import MultiPoint


# ---------------------------------------------------------------------------
# Öffentliche Hauptfunktion
# ---------------------------------------------------------------------------

def reorder_points(points_mm: np.ndarray, params: dict, layer_idx: int) -> np.ndarray:
    """
    Nimmt existierende Punkte (N×2 Array in mm) und gibt sie in neuer Reihenfolge zurück.

    Ablauf:
      1. Polygon (konvexe Hülle) aus Punkten berechnen – für Segmentierung nötig.
      2. Stufe 1: Punkte in Segmente aufteilen.
      3. Stufe 2: Innerhalb jedes Segments sortieren.
      4. Alle Ergebnisse zu einem Array zusammenführen.

    :param points_mm: np.ndarray (N, 2) – original Punkte in mm.
    :param params:    Parameter-Dict aus render_strategy_ui().
    :param layer_idx: Schichtindex (für schichtweise Rotation).
    :return:          np.ndarray (N, 2) – gleiche Punkte, neue Reihenfolge.
    """
    if len(points_mm) == 0:
        return points_mm

    rotation = (layer_idx * params.get('rotation_angle_deg', 67.0)) % 360.0

    # Polygon aus Punkten (für Segmentierungsalgorithmen wie Spiralzonen)
    polygon = MultiPoint(points_mm).convex_hull

    # Stufe 1: Segmentierung
    seg_type = params.get('segmentation', 'Keine Segmentierung')
    if seg_type == 'Keine Segmentierung':
        segments = [points_mm]
    else:
        segments = segment_points(points_mm, polygon, params, rotation)

    # Stufe 2: Mikro-Sortierung innerhalb jedes Segments
    reordered = []
    for seg_pts in segments:
        if len(seg_pts) == 0:
            continue
        sorted_pts = sort_within_segment(seg_pts, params, rotation)
        reordered.append(sorted_pts)

    return np.vstack(reordered) if reordered else points_mm


# ---------------------------------------------------------------------------
# Stufe 1: Segmentierung
# ---------------------------------------------------------------------------

def segment_points(points_mm: np.ndarray, polygon, params: dict, rotation: float):
    """Dispatcht an die gewählte Segmentierungsfunktion."""
    seg_type = params.get('segmentation', 'Keine Segmentierung')
    seg_size = params.get('seg_size', 5.0)
    seg_order = params.get('seg_order', 'Schachbrett (schwarz→weiß)')

    if 'Schachbrett' in seg_type:
        return _segment_chessboard(points_mm, seg_size, seg_order)
    elif 'Streifen' in seg_type:
        return _segment_stripes(points_mm, seg_size, rotation, seg_order)
    elif 'Hexagonal' in seg_type:
        return _segment_hexagonal(points_mm, seg_size, seg_order)
    elif 'Spiralzonen' in seg_type or 'Konzentrisch' in seg_type:
        return _segment_spiral_zones(points_mm, polygon, seg_size, seg_order)
    return [points_mm]


def _segment_chessboard(points_mm: np.ndarray, seg_size: float, seg_order: str):
    """Schachbrett-Segmentierung: erst Phase A ((row+col)%2==0), dann Phase B."""
    if len(points_mm) == 0:
        return []

    minx = points_mm[:, 0].min()
    miny = points_mm[:, 1].min()

    col_idx = ((points_mm[:, 0] - minx) / seg_size).astype(int)
    row_idx = ((points_mm[:, 1] - miny) / seg_size).astype(int)

    cell_keys = np.stack([row_idx, col_idx], axis=1)  # (N, 2)
    unique_cells = list(set(map(tuple, cell_keys.tolist())))

    phase_a = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 0]
    phase_b = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 1]

    phase_a = _order_cells(phase_a, seg_order)
    phase_b = _order_cells(phase_b, seg_order)
    ordered = phase_a + phase_b

    segments = []
    for (r, c) in ordered:
        mask = (row_idx == r) & (col_idx == c)
        pts = points_mm[mask]
        if len(pts) > 0:
            segments.append(pts)
    return segments


def _segment_stripes(points_mm: np.ndarray, seg_size: float, rotation: float, seg_order: str):
    """Streifen-Segmentierung: parallele Bänder senkrecht zur aktuellen Hatch-Richtung."""
    if len(points_mm) == 0:
        return []

    cos_r = np.cos(np.radians(rotation))
    sin_r = np.sin(np.radians(rotation))
    cx, cy = points_mm.mean(axis=0)
    rel = points_mm - [cx, cy]
    # Projektion auf die Richtung senkrecht zum Hatch-Vektor
    rot_y = rel[:, 0] * sin_r + rel[:, 1] * cos_r

    miny = rot_y.min()
    stripe_idx = ((rot_y - miny) / seg_size).astype(int)
    unique_stripes = sorted(set(stripe_idx.tolist()))

    if 'Zufällig' in seg_order:
        rng = np.random.default_rng(42)
        unique_stripes = list(unique_stripes)
        rng.shuffle(unique_stripes)

    segments = []
    for s in unique_stripes:
        pts = points_mm[stripe_idx == s]
        if len(pts) > 0:
            segments.append(pts)
    return segments


def _segment_hexagonal(points_mm: np.ndarray, seg_size: float, seg_order: str):
    """Hexagonale Segmentierung: versetztes Gitter, alternierend Phase A/B."""
    if len(points_mm) == 0:
        return []

    h = seg_size * np.sqrt(3)   # horizontaler Abstand zwischen Hex-Mittelpunkten
    v = seg_size * 1.5           # vertikaler Abstand

    minx = points_mm[:, 0].min()
    miny = points_mm[:, 1].min()

    row_idx = ((points_mm[:, 1] - miny) / v).astype(int)
    x_offset = np.where(row_idx % 2 == 1, h / 2.0, 0.0)
    col_idx = ((points_mm[:, 0] - minx - x_offset) / h).astype(int)

    cell_keys = np.stack([row_idx, col_idx], axis=1)
    unique_cells = list(set(map(tuple, cell_keys.tolist())))

    phase_a = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 0]
    phase_b = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 1]
    ordered = phase_a + phase_b

    segments = []
    for (r, c) in ordered:
        mask = (row_idx == r) & (col_idx == c)
        pts = points_mm[mask]
        if len(pts) > 0:
            segments.append(pts)
    return segments


def _segment_spiral_zones(points_mm: np.ndarray, polygon, seg_size: float, seg_order: str):
    """Spiralzonen: konzentrische Ringe um den Polygon-Schwerpunkt."""
    if len(points_mm) == 0:
        return []

    try:
        cx, cy = polygon.centroid.x, polygon.centroid.y
    except Exception:
        cx, cy = points_mm[:, 0].mean(), points_mm[:, 1].mean()

    dist = np.sqrt((points_mm[:, 0] - cx) ** 2 + (points_mm[:, 1] - cy) ** 2)
    ring_idx = (dist / seg_size).astype(int)
    unique_rings = sorted(set(ring_idx.tolist()))

    # außen→innen (Standard) oder innen→außen
    if 'außen' in seg_order:
        unique_rings = sorted(unique_rings, reverse=True)

    segments = []
    for r in unique_rings:
        pts = points_mm[ring_idx == r]
        if len(pts) > 0:
            segments.append(pts)
    return segments


def _order_cells(cells: list, seg_order: str) -> list:
    """Sortiert Zell-Tupel (row, col) nach der gewählten Reihenfolge."""
    if not cells:
        return cells
    if 'Spirale (außen' in seg_order:
        return _cells_by_dist(cells, reverse=True)
    elif 'Spirale (innen' in seg_order:
        return _cells_by_dist(cells, reverse=False)
    elif 'Zufällig' in seg_order:
        arr = list(cells)
        rng = np.random.default_rng(42)
        rng.shuffle(arr)
        return arr
    elif 'Sequentiell' in seg_order:
        return sorted(cells, key=lambda rc: (rc[0], rc[1]))
    # Standard: Schachbrett (sortiert nach row, col)
    return sorted(cells, key=lambda rc: (rc[0], rc[1]))


def _cells_by_dist(cells: list, reverse: bool) -> list:
    rows = [r for r, c in cells]
    cols = [c for r, c in cells]
    cr, cc = np.mean(rows), np.mean(cols)
    dist = [(r - cr) ** 2 + (c - cc) ** 2 for r, c in cells]
    return [cell for _, cell in sorted(zip(dist, cells), reverse=reverse)]


# ---------------------------------------------------------------------------
# Stufe 2: Mikro-Sortierung
# ---------------------------------------------------------------------------

def sort_within_segment(points: np.ndarray, params: dict, rotation: float) -> np.ndarray:
    """Dispatcht an die gewählte Mikro-Sortierfunktion."""
    strategy = params.get('micro_strategy', 'Raster (Zick-Zack)')

    if strategy in ('Raster (Zick-Zack)', 'Spot Consecutive'):
        return sort_raster(points, params, rotation)
    elif strategy == 'Spot Ordered':
        return sort_spot_ordered(points, params, rotation)
    elif strategy == 'Ghost Beam':
        return sort_ghost_beam(points, params, rotation)
    elif strategy == 'Hilbert-Kurve':
        return sort_hilbert(points, params)
    elif strategy == 'Spiral':
        return sort_spiral(points, params)
    elif strategy == 'Peano-Kurve':
        return sort_peano(points, params)
    return points


def sort_raster(points: np.ndarray, params: dict, rotation: float) -> np.ndarray:
    """
    Raster-Sortierung (Zick-Zack):
    - Transformiere Punkte ins rotierte Koordinatensystem (nur für Sortierung).
    - Quantisiere Y in Hatch-Zeilen.
    - Sortiere abwechselnd nach X (Zick-Zack).
    """
    hatch_mm = params.get('hatch_spacing', 200.0) / 1000.0

    cos_r = np.cos(np.radians(-rotation))
    sin_r = np.sin(np.radians(-rotation))
    cx, cy = points.mean(axis=0)
    rel = points - [cx, cy]
    rot_x = rel[:, 0] * cos_r - rel[:, 1] * sin_r
    rot_y = rel[:, 0] * sin_r + rel[:, 1] * cos_r

    y_bins = np.round(rot_y / hatch_mm).astype(int)
    indices = np.arange(len(points))
    unique_bins = np.unique(y_bins)

    sorted_indices = []
    for i, yb in enumerate(unique_bins):
        mask = y_bins == yb
        row_idx = indices[mask]
        row_x = rot_x[mask]
        order = np.argsort(row_x)
        if i % 2 == 1:          # Zick-Zack: jede zweite Zeile umkehren
            order = order[::-1]
        sorted_indices.extend(row_idx[order])

    return points[sorted_indices]


def sort_spot_ordered(points: np.ndarray, params: dict, rotation: float) -> np.ndarray:
    """
    Spot Ordered (Multipass):
    Raster-Sortierung, dann Multipass-Umordnung: Pass 1 jeden (skip+1)-ten Punkt,
    Pass 2 versetzt usw. – verhindert lokale Hitzeakkumulation.
    """
    base = sort_raster(points, params, rotation)
    skip = max(1, int(params.get('spot_skip', 2)))

    passes = [base[offset::skip + 1] for offset in range(skip + 1)]
    non_empty = [p for p in passes if len(p) > 0]
    return np.vstack(non_empty) if non_empty else base


def sort_ghost_beam(points: np.ndarray, params: dict, rotation: float) -> np.ndarray:
    """
    Ghost Beam:
    Raster-Sortierung, dann Interleave: primärer Punkt + nachlaufender Geistpunkt
    (P1 → S1 → P2 → S2 …). Der Geistpunkt liegt ~ghost_lag µm hinter dem Primärpunkt.
    """
    base = sort_raster(points, params, rotation)
    ghost_lag_mm = params.get('ghost_lag', 1000.0) / 1000.0
    point_spacing_mm = params.get('point_spacing', 100.0) / 1000.0
    lag_count = max(1, int(ghost_lag_mm / point_spacing_mm))

    N = len(base)
    result = np.empty((N * 2, 2), dtype=base.dtype)
    for i in range(N):
        result[2 * i] = base[i]
        result[2 * i + 1] = base[max(0, i - lag_count)]
    return result


def sort_hilbert(points: np.ndarray, params: dict) -> np.ndarray:
    """
    Hilbert-Kurve:
    Berechnet für jeden Punkt den Hilbert-Index auf einem 2^order × 2^order Grid
    und sortiert die Punkte danach.
    """
    order = int(params.get('hilbert_order', 4))
    n = 2 ** order

    if len(points) == 0:
        return points

    minx, miny = points[:, 0].min(), points[:, 1].min()
    maxx, maxy = points[:, 0].max(), points[:, 1].max()
    eps = 1e-9

    ix = np.clip(((points[:, 0] - minx) / (maxx - minx + eps) * (n - 1)).astype(int), 0, n - 1)
    iy = np.clip(((points[:, 1] - miny) / (maxy - miny + eps) * (n - 1)).astype(int), 0, n - 1)

    h_indices = np.array([_xy2d_hilbert(n, int(x), int(y)) for x, y in zip(ix, iy)])
    return points[np.argsort(h_indices)]


def _xy2d_hilbert(n: int, x: int, y: int) -> int:
    """Konvertiert Gitterkoordinaten (x, y) in den 1D Hilbert-Kurven-Index."""
    d = 0
    s = n // 2
    while s > 0:
        rx = 1 if (x & s) > 0 else 0
        ry = 1 if (y & s) > 0 else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        s //= 2
    return d


def sort_spiral(points: np.ndarray, params: dict) -> np.ndarray:
    """
    Spiral:
    Berechnet für jeden Punkt (Abstand zum Schwerpunkt, Winkel) und sortiert
    dann ringweise von außen nach innen (oder innen nach außen).
    """
    direction = params.get('spiral_direction', 'inward')
    hatch_mm = params.get('hatch_spacing', 200.0) / 1000.0

    if len(points) == 0:
        return points

    cx, cy = points.mean(axis=0)
    dx = points[:, 0] - cx
    dy = points[:, 1] - cy
    dist = np.sqrt(dx ** 2 + dy ** 2)
    angle = np.arctan2(dy, dx)

    ring_idx = np.round(dist / hatch_mm).astype(int)

    if direction == 'inward':
        order_idx = np.lexsort((angle, -ring_idx))
    else:
        order_idx = np.lexsort((angle, ring_idx))

    return points[order_idx]


def sort_peano(points: np.ndarray, params: dict) -> np.ndarray:
    """
    Peano-Kurve (Boustrophedon-Näherung):
    Quantisiert Punkte auf ein n×n Grid und sortiert nach Zeilen, abwechselnd
    links→rechts und rechts→links. Entspricht einer Schlangenlinie auf feinem Grid –
    ähnlich wie Peano, ohne den vollen rekursiven Aufwand.
    """
    order = int(params.get('hilbert_order', 4))
    n = 3 ** min(order, 5)   # max. 3^5 = 243 für sinnvolle Laufzeit

    if len(points) == 0:
        return points

    minx, miny = points[:, 0].min(), points[:, 1].min()
    maxx, maxy = points[:, 0].max(), points[:, 1].max()
    eps = 1e-9

    ix = np.clip(((points[:, 0] - minx) / (maxx - minx + eps) * (n - 1)).astype(int), 0, n - 1)
    iy = np.clip(((points[:, 1] - miny) / (maxy - miny + eps) * (n - 1)).astype(int), 0, n - 1)

    # Boustrophedon-Key: in geraden Zeilen ix vorwärts, in ungeraden rückwärts
    peano_x = np.where(iy % 2 == 0, ix, n - 1 - ix)
    peano_key = iy * n + peano_x

    return points[np.argsort(peano_key)]
