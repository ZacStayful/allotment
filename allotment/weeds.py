"""Weed pressure model (§22). Four additive drivers, then corrected by what you
actually observe, so after a season the map is evidence rather than theory.

With no-dig the map should fade year on year as the buried seed bank stays
buried. If it doesn't, something in the method is wrong - which is itself worth
knowing.
"""

import math

from . import config
from .sun import GN, GRID

DRIVERS = [
    ("woodland seed rain", 1.00),
    ("grass creeping in from the plot edge", 0.85),
    ("path and hardstanding edge", 0.35),
    ("bare ground", 0.45),
    ("proximity to the compost bays", 0.40),
    ("bed perimeter", 0.25),
]
NORMALISER = 2.2
COMPOST_XY = (9.9, 8.1)


def drivers_at(zones, x, y):
    """[(name, contribution)] at a point, so the map can explain a score."""
    out = []
    W, D = config.PLOT_W, config.PLOT_D

    seed_rain = max(0.0, 1 - (W - x) / 4.5) * 1.00
    if seed_rain > 0:
        out.append(("woodland seed rain", seed_rain))

    edge = min(x, W - x, y, D - y)
    grass = max(0.0, 1 - edge / 1.2) * 0.85
    if grass > 0:
        out.append(("grass creeping in from the plot edge", grass))

    if x < 2.2:
        out.append(("path and hardstanding edge", 0.35))

    for z in zones:
        if z["id"] in ("spud", "green", "green2") and _inside(z, x, y, 0):
            out.append(("bare or thinly covered ground", 0.45))
            break

    dc = math.hypot(x - COMPOST_XY[0], y - COMPOST_XY[1])
    comp = max(0.0, 1 - dc / 2.0) * 0.40
    if comp > 0:
        out.append(("proximity to the compost bays", comp))

    for z in zones:
        if z["id"].startswith("b") and len(z["id"]) == 2 and _inside(z, x, y, 0.35):
            out.append(("bed perimeter", 0.25))
            break

    return out


def _inside(z, x, y, pad):
    return (z["x"] - pad <= x <= z["x"] + z["w"] + pad and
            z["y"] - pad <= y <= z["y"] + z["d"] + pad)


def predicted(zones):
    grid = [[0.0] * GN for _ in range(GN)]
    for i in range(GN):
        x = (i + 0.5) * GRID
        for j in range(GN):
            y = (j + 0.5) * GRID
            s = sum(v for _, v in drivers_at(zones, x, y))
            grid[i][j] = min(1.0, s / NORMALISER)
    return grid


def observed_grid(conn):
    """Observations at points, spread over a 1 m radius. Returns (value, weight)."""
    obs = conn.execute("SELECT x,y,observed FROM weed_observations "
                       "WHERE x IS NOT NULL AND y IS NOT NULL").fetchall()
    val = [[0.0] * GN for _ in range(GN)]
    wt = [[0.0] * GN for _ in range(GN)]
    for o in obs:
        for i in range(GN):
            x = (i + 0.5) * GRID
            for j in range(GN):
                y = (j + 0.5) * GRID
                dist = math.hypot(x - o["x"], y - o["y"])
                if dist > 1.0:
                    continue
                w = 1.0 - dist
                val[i][j] += o["observed"] * w
                wt[i][j] += w
    return val, wt


def current(conn, zones):
    """Predicted, progressively overridden by observation."""
    pred = predicted(zones)
    val, wt = observed_grid(conn)
    out = [[0.0] * GN for _ in range(GN)]
    for i in range(GN):
        for j in range(GN):
            w = wt[i][j]
            if w <= 0:
                out[i][j] = pred[i][j]
            else:
                blend = min(0.8, 0.25 * w)
                out[i][j] = round(pred[i][j] * (1 - blend) + (val[i][j] / w) * blend, 3)
    return out


def zone_pressure(conn, zones=None):
    """Mean pressure per zone, worst first. Orders the 20-minute arrival weed."""
    if zones is None:
        zones = [dict(r) for r in conn.execute(
            "SELECT id,name,x,y,w,d,height_m,growable FROM zones").fetchall()]
    grid = current(conn, zones)
    out = []
    for z in zones:
        vals = []
        for i in range(GN):
            x = (i + 0.5) * GRID
            if not (z["x"] <= x <= z["x"] + z["w"]):
                continue
            for j in range(GN):
                y = (j + 0.5) * GRID
                if z["y"] <= y <= z["y"] + z["d"]:
                    vals.append(grid[i][j])
        if vals:
            out.append({"zone": z["id"], "name": z["name"],
                        "pressure": round(sum(vals) / len(vals), 2)})
    return sorted(out, key=lambda r: -r["pressure"])


def weeding_order(conn, minutes=20):
    """Split the arrival weed across the worst zones first (§24)."""
    ranked = [z for z in zone_pressure(conn) if z["pressure"] > 0.05][:4]
    total = sum(z["pressure"] for z in ranked) or 1
    out = []
    for z in ranked:
        out.append({"zone": z["zone"], "name": z["name"], "pressure": z["pressure"],
                    "minutes": max(2, int(round(minutes * z["pressure"] / total)))})
    return out


def log_observation(conn, when, observed, x=None, y=None, zone_id=None, minutes=None,
                    notes=None):
    if x is None and zone_id:
        z = conn.execute("SELECT x,y,w,d FROM zones WHERE id=?", (zone_id,)).fetchone()
        if z:
            x, y = z["x"] + z["w"] / 2, z["y"] + z["d"] / 2
    conn.execute("INSERT INTO weed_observations(date,zone_id,x,y,observed,minutes,notes) "
                 "VALUES(?,?,?,?,?,?,?)", (str(when), zone_id, x, y, observed, minutes, notes))
    conn.commit()
