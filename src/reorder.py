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
      5. Ghost Beam (falls gewählt) wird NACH der Zusammenführung auf den Gesamtpfad
         angewandt – nicht pro Segment, da es sonst bei kleinen Segmenten entartet.

    :param points_mm: np.ndarray (N, 2) – original Punkte in mm.
    :param params:    Parameter-Dict aus render_strategy_ui().
    :param layer_idx: Schichtindex (für schichtweise Rotation).
    :return:          np.ndarray (N, 2) – gleiche Punkte, neue Reihenfolge.
                      (Bei Ghost Beam: 2×N Punkte, da Primär- + Geistpunkte interleaved.)
    """
    if len(points_mm) == 0:
        return points_mm

    rotation = (layer_idx * params.get('rotation_angle_deg', 67.0)) % 360.0
    micro_strategy = params.get('micro_strategy', 'Raster (Zick-Zack)')

    # Polygon aus Punkten (für Segmentierungsalgorithmen wie Spiralzonen)
    polygon = MultiPoint(points_mm).convex_hull

    # Stufe 1: Segmentierung
    seg_type = params.get('segmentation', 'Keine Segmentierung')
    if seg_type == 'Keine Segmentierung':
        segments = [points_mm]
    else:
        segments = segment_points(points_mm, polygon, params, rotation)

    # Stufe 2: Mikro-Sortierung innerhalb jedes Segments.
    # Ghost Beam: pro Segment nur Raster-Vorsortierung; das Ghost-Interleaving
    # erfolgt erst nach der Zusammenführung auf dem Gesamtpfad (siehe unten).
    reordered = []
    for seg_pts in segments:
        if len(seg_pts) == 0:
            continue
        if micro_strategy == 'Ghost Beam':
            sorted_pts = sort_raster(seg_pts, params, rotation)
        else:
            sorted_pts = sort_within_segment(seg_pts, params, rotation)
        reordered.append(sorted_pts)

    combined = np.vstack(reordered) if reordered else points_mm

    # Ghost Beam auf den vollständigen Pfad anwenden
    if micro_strategy == 'Ghost Beam':
        combined = sort_ghost_beam(combined, params, rotation)

    return combined


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

# Funktion um das Schachbrett zu segmentieren
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

    # Hier werden die Phasen A und B definiert, welche die zellen beschreiben, die in dieser Phase abgearbeitet werden
    phase_a = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 0]
    phase_b = [(r, c) for (r, c) in unique_cells if (r + c) % 2 == 1]

    #Hier werden die Phasen A und B sortiert 
    phase_a = _order_cells(phase_a, seg_order)
    phase_b = _order_cells(phase_b, seg_order)
    ordered = phase_a + phase_b

    # Hier werden die Segmente zusammengefügt
    segments = []
    for (r, c) in ordered:
        mask = (row_idx == r) & (col_idx == c)
        pts = points_mm[mask]
        if len(pts) > 0:
            segments.append(pts)
    return segments

# Funktion um Streifen zu segmentieren
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

    # Hier werden die Segmente zusammengefügt
    segments = []
    for s in unique_stripes:
        pts = points_mm[stripe_idx == s]
        if len(pts) > 0:
            segments.append(pts)
    return segments

# Funktion um Hexagonale zu segmentieren
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
    """Dispatcht an die gewählte Mikro-Sortierfunktion.

    Hinweis: Ghost Beam wird NICHT hier dispatcht – reorder_points() wendet
    sort_ghost_beam() nach der Zusammenführung aller Segmente auf den Gesamtpfad an.
    """
    strategy = params.get('micro_strategy', 'Raster (Zick-Zack)')

    if strategy in ('Raster (Zick-Zack)', 'Spot Consecutive'):
        return sort_raster(points, params, rotation)
    elif strategy == 'Spot Ordered':
        return sort_spot_ordered(points, params, rotation)
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
    Erkennt die natürlichen Y-Linien im Input via Rundung auf 50 µm und sortiert
    die Punkte zeilenweise abwechselnd nach X (Zick-Zack).

    Wichtig: Die vom Slicer vorgegebene Linienstruktur wird NICHT verändert –
    keine Rotation der Koordinaten, keine hatch_spacing-basierte Quantisierung.
    Rotation und hatch_spacing sind für diesen Sort irrelevant, da die Linien
    bereits in der korrekten Orientierung und mit dem korrekten Abstand vorliegen.
    """
    # Natürliche Y-Cluster im Input erkennen (50 µm Raster = halber Punktabstand)
    y_rounded = np.round(points[:, 1] / 0.05) * 0.05
    unique_ys = np.unique(y_rounded)

    sorted_indices = []
    for i, yc in enumerate(unique_ys):
        mask = y_rounded == yc
        row_idx = np.where(mask)[0]
        row_x = points[mask, 0]
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
    Ghost Beam – Interleaving auf bereits sortiertem Pfad:
    Erzeugt P1 → S1 → P2 → S2 … wobei S_i ein nachlaufender Geistpunkt
    (~ghost_lag µm hinter P_i) ist. Verdoppelt die Punktanzahl.

    Erwartet einen bereits raster-sortierten Pfad als Input (reorder_points()
    übernimmt die Vorsortierung pro Segment vor diesem Aufruf).

    Sicherheitscheck: Wenn N < 2 * lag_count (Segment zu klein für den Lag),
    wird lag_count dynamisch auf max(1, N // 4) reduziert.
    """
    ghost_lag_mm = params.get('ghost_lag', 1000.0) / 1000.0
    point_spacing_mm = params.get('point_spacing', 100.0) / 1000.0
    lag_count = max(1, int(ghost_lag_mm / point_spacing_mm))

    N = len(points)
    if N < 2 * lag_count:
        lag_count = max(1, N // 4)

    result = np.empty((N * 2, 2), dtype=points.dtype)
    for i in range(N):
        result[2 * i] = points[i]
        result[2 * i + 1] = points[max(0, i - lag_count)]
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
