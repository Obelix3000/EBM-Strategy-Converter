import numpy as np

MATERIALS = {
    "MicroMelt 23 (PM HSS)": {
        "density_kg_m3": 8170,
        "specific_heat_J_kgK": 420,
        "thermal_conductivity_W_mK": 25.0,
        "melting_point_C": 1430,
    },
    "IN718 (Inconel)": {
        "density_kg_m3": 7451,
        "specific_heat_J_kgK": 600,
        "thermal_conductivity_W_mK": 26.6,
        "melting_point_C": 1337,
    },
    "Ti-6Al-4V": {
        "density_kg_m3": 4430,
        "specific_heat_J_kgK": 526,
        "thermal_conductivity_W_mK": 6.7,
        "melting_point_C": 1604,
    },
}

def calc_diffusivity(mat_name):
    mat = MATERIALS[mat_name]
    return mat["thermal_conductivity_W_mK"] / (
        mat["density_kg_m3"] * mat["specific_heat_J_kgK"])

def compute_heat_accumulation(points_xy, mat_name, 
                                t_point_us=13.0, lookback=200):
    """
    Berechnet einen Wärmeakkumulations-Index für jeden Punkt.
    
    points_xy: np.array shape (N, 2) in mm
    mat_name: Schlüssel aus MATERIALS dict
    t_point_us: Punkthaltezeit in Mikrosekunden
    lookback: Anzahl vorheriger Punkte die berücksichtigt werden
    
    Returns: np.array shape (N,) mit Wärme-Index (0 = kalt, 1 = max)
    """
    alpha = calc_diffusivity(mat_name)  # m²/s
    alpha_mm2_us = alpha * 1e6 * 1e-6  # Umrechnung in mm²/µs
    t_point = t_point_us  # µs
    
    N = len(points_xy)
    heat = np.zeros(N)
    
    for i in range(1, N):
        j_start = max(0, i - lookback)
        # Distanzen zu allen vorherigen Punkten im Lookback-Fenster
        dists = np.sqrt(np.sum((points_xy[j_start:i] - points_xy[i])**2, axis=1))
        # Zeitliche Distanz in µs
        dt = np.arange(i - j_start, 0, -1) * t_point
        # Gaußsche Wärmediffusion: exp(-d² / (4·α·t))
        exponent = -(dists**2) / (4.0 * alpha_mm2_us * dt + 1e-30)
        heat[i] = np.sum(np.exp(exponent))
    
    # Normalisierung auf [0, 1]
    if heat.max() > 0:
        heat = heat / heat.max()
    return heat
