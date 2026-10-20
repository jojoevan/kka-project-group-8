"""Klaster hotspot instances from a saved NASA FIRMS VIIRS snapshot (ADR-0001).

The snapshot CSV is untrusted input: it is only parsed as data (numeric and confidence columns).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from src.instance import Instance, haversine_matrix

COLUMNS = ["latitude", "longitude", "confidence", "frp"]


def load_hotspots(path, confidence, bboxes):
    """Hotspots with a confidence in `confidence` that lie inside any bounding box.

    bboxes maps a region name to [lat_min, lat_max, lon_min, lon_max]; the matched region is kept in
    column `region`. Rows with an unparsable coordinate or FRP are dropped."""
    path = Path(path)
    if not path.exists(): raise FileNotFoundError(f"Snapshot FIRMS tidak ditemukan: {path}")
    raw = pd.read_csv(path, usecols=COLUMNS, dtype=str)
    h = pd.DataFrame({"lat": pd.to_numeric(raw.latitude, errors="coerce"),
                      "lon": pd.to_numeric(raw.longitude, errors="coerce"),
                      "confidence": raw.confidence.str.strip().str.lower(),
                      "frp": pd.to_numeric(raw.frp, errors="coerce")}).dropna()
    h = h[h.confidence.isin([c.lower() for c in confidence]) & (h.frp >= 0)]
    h["region"] = None
    for name, (lat0, lat1, lon0, lon1) in bboxes.items():
        inside = h.region.isna() & h.lat.between(lat0, lat1) & h.lon.between(lon0, lon1)
        h.loc[inside, "region"] = name
    return h[h.region.notna()].reset_index(drop=True)


def kmeans(X, k, seed=0, max_iter=300):
    """Lloyd's k-means with k-means++ seeding; deterministic for a seed. Returns (labels, centres).

    An empty cluster is re-seeded with the point farthest from its current centre."""
    X = np.asarray(X, float); n = len(X)
    if not 1 <= k <= n: raise ValueError(f"k={k} harus di antara 1 dan jumlah hotspot ({n})")
    rng = np.random.default_rng(seed)
    centres = [X[int(rng.integers(n))]]
    d2 = ((X - centres[0]) ** 2).sum(1)
    for _ in range(1, k):
        if d2.sum() <= 0: raise ValueError(f"Hotspot berbeda lokasi kurang dari k={k}")
        centres.append(X[int(rng.choice(n, p=d2 / d2.sum()))])
        d2 = np.minimum(d2, ((X - centres[-1]) ** 2).sum(1))
    C = np.array(centres); labels = None
    for _ in range(max_iter):
        D = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
        new = D.argmin(1)
        for j in np.setdiff1d(np.arange(k), new):  # empty cluster
            far = int(D[np.arange(n), new].argmax()); new[far] = j; D[far] = np.inf
        if labels is not None and np.array_equal(new, labels): break
        labels = new
        C = np.array([X[labels == j].mean(0) for j in range(k)])
    return labels, C


def _risk_from_frp(frp_sum):
    """Σ FRP -> log1p -> min-max over the clusters (all equal -> 1)."""
    v = np.log1p(np.asarray(frp_sum, float)); span = v.max() - v.min()
    return (v - v.min()) / span if span > 0 else np.ones_like(v)


def build_firms_instance(hotspots, k, depot, seed=0, speed=200., detour=1.15, dwell=1., time_limit=72.,
                         g0=.01):
    """Instance of the Depot plus k Klaster hotspot nodes, and a node table (name, lat, lon, hotspots,
    frp_sum, risk, region).

    Hotspots are clustered with k-means on (lat, lon * cos lat). A node sits at its cluster centre,
    or at the member hotspot closest to it if the centre falls outside the member's bounding boxes
    (a cluster spanning two regions). Risiko = Σ FRP -> log1p -> min-max over the clusters. Clusters
    have no operational data, so decay is constant (ops = 0, g = g0). Nodes are numbered by Risiko,
    highest first. depot is {name, lat, lon}."""
    h = hotspots.reset_index(drop=True)
    X = np.c_[h.lat, h.lon * np.cos(np.radians(h.lat))]
    labels, _ = kmeans(X, k, seed)
    rows = []
    for j in range(k):
        m = h[labels == j]; lat, lon = m.lat.mean(), m.lon.mean()
        if m.region.nunique() > 1:  # a centre inside one convex box always stays inside it
            near = ((m.lat - lat) ** 2 + (m.lon - lon) ** 2).idxmin(); lat, lon = m.lat[near], m.lon[near]
        rows.append({"lat": float(lat), "lon": float(lon), "hotspots": len(m), "frp_sum": float(m.frp.sum()),
                     "region": m.region.mode().iloc[0]})
    nodes = pd.DataFrame(rows)
    nodes["risk"] = _risk_from_frp(nodes.frp_sum)
    nodes = nodes.sort_values(["risk", "lat", "lon"], ascending=[False, True, True], kind="stable")
    nodes = nodes.reset_index(drop=True)
    nodes.insert(0, "name", [f"Klaster {i + 1}" for i in range(k)])
    lat = np.r_[depot["lat"], nodes.lat]; lon = np.r_[depot["lon"], nodes.lon]
    dist = haversine_matrix(lat, lon) * detour
    inst = Instance([depot["name"]] + nodes.name.tolist(), np.r_[0., nodes.risk], np.zeros(k + 1), dist, 0,
                    speed, dwell, time_limit, g0, 0.)
    return inst, nodes
