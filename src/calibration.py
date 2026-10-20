"""Calibrate the main Batas waktu misi so the province instance is a real orienteering problem.

Greedy is run on the instance for each candidate time limit; the smallest candidate whose visited
fraction (non-depot nodes) lies in the target range is chosen. If none does, the candidate closest to
the range is returned with in_target=False.

    python -m src.calibration [--write]   # n=38, scenario 2026; --write records it in config.yaml
"""
import argparse
import dataclasses
import re
from pathlib import Path
import pandas as pd
from src.algorithms.greedy import solve as greedy

CANDIDATE_TIME_LIMITS = (24, 48, 72, 120)
TARGET_FRACTION = (.4, .6)


def calibrate_time_limit(inst, candidates=CANDIDATE_TIME_LIMITS, target=TARGET_FRACTION):
    """Returns time_limit, visited_fraction, in_target and the full table (one row per candidate)."""
    lo, hi = target; n = len(inst.names) - 1; rows = []
    for T in sorted(candidates):
        visited = len(greedy(dataclasses.replace(inst, time_limit=float(T)))["best_route"]["route"])
        rows.append({"time_limit_h": T, "visited": visited, "visited_fraction": visited / n})
    table = pd.DataFrame(rows)
    hits = table[table.visited_fraction.between(lo, hi)]
    if len(hits):
        row = hits.iloc[0]
    else:
        gap = (lo - table.visited_fraction).clip(lower=0) + (table.visited_fraction - hi).clip(lower=0)
        row = table.loc[gap.idxmin()]
    return {"time_limit": int(row.time_limit_h), "visited": int(row.visited),
            "visited_fraction": float(row.visited_fraction), "in_target": bool(len(hits)), "table": table}


def write_time_limit(config_path, value):
    """Replace the time_limit_hours line in config.yaml, keeping every other line as-is."""
    path = Path(config_path); text = path.read_text(encoding="utf8")
    line = (f"time_limit_hours: {value}  # Batas waktu misi; dikalibrasi greedy n=38 skenario 2026 "
            f"(python -m src.calibration)")
    new, count = re.subn(r"^time_limit_hours:.*$", line, text, flags=re.M)
    if count != 1: raise ValueError("config.yaml harus berisi tepat satu baris time_limit_hours")
    path.write_text(new, encoding="utf8")


def main():
    from src.config import load_config, province_coords, province_features, province_instance
    from src.data_prep import ROOT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--write", action="store_true", help="catat nilai terpilih di config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    inst = province_instance(cfg, province_features(cfg), province_coords(), n=38, scenario="2026")
    out = calibrate_time_limit(inst)  # the configured time limit is replaced by each candidate
    print(out["table"].rename(columns={"time_limit_h": "batas_waktu_jam", "visited": "terkunjungi",
                                       "visited_fraction": "fraksi_terkunjungi"}).to_string(index=False))
    status = "dalam target" if out["in_target"] else "TIDAK ada kandidat dalam target; dipilih yang terdekat"
    print(f"Batas waktu misi terpilih: {out['time_limit']} jam "
          f"({out['visited_fraction']:.0%} node terkunjungi, {status})")
    if args.write:
        write_time_limit(args.config, out["time_limit"]); print(f"Tercatat di {args.config}")


if __name__ == "__main__":
    main()
