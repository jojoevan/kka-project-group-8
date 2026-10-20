
"""Reproducible experiment runner. Use --quick for a smoke run."""
import argparse, sys, json, time, logging
import yaml
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.data_prep import prepare, SCENARIOS, OPS_SCENARIO
from src.instance import build_instance, INSTANCE_SIZES
from src.algorithms import SOLVERS
from src.algorithms.exact import MAX_NODES as EXACT_MAX_NODES

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--quick",action="store_true")
    args=ap.parse_args(); logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s")
    cfg=yaml.safe_load((ROOT/"config.yaml").read_text(encoding="utf8"))
    w=cfg["weights"]; f,disc,checks=prepare(weights=(w["hist"],w["cur"],w["ops"]),gamma=cfg["gamma"])
    coords=pd.read_csv(ROOT/"data/external/province_coords.csv")
    out=ROOT/"results"
    for sub in ["raw","tables","routes","figures"]: (out/sub).mkdir(parents=True,exist_ok=True)
    sizes=[6] if args.quick else list(INSTANCE_SIZES)
    seeds=2 if args.quick else cfg["seeds"]; budget=500 if args.quick else cfg["fitness_evaluations"]
    rows=[]; cases=[]
    for year in [OPS_SCENARIO] if args.quick else list(SCENARIOS):
        for n in sizes:
            inst=build_instance(f,coords,n=n,scenario=year,depot_name=cfg["depot"],speed=cfg["speed_kmh"],
                                detour=cfg["detour_factor"],dwell=cfg["dwell_hours"],time_limit=cfg["time_limit_hours"],
                                g0=cfg["decay_g0"],kappa=cfg["decay_kappa"])
            algos={name:(lambda seed,fn=SOLVERS[name]:fn(inst,budget=budget,seed=seed)) for name in ("Greedy","HC","SA","GA")}
            for seed in range(seeds):
                for name,fn in algos.items():
                    res=fn(seed); rows.append({"scenario":year,"n":n,"seed":seed,"algorithm":name,
                        "fitness":res["best_fitness"],"runtime_s":res["runtime"],"evals":res["evals"]})
                    if seed==0:
                        cases.append((year,n,name,res))
            if n<=EXACT_MAX_NODES:
                ex=SOLVERS["Exact"](inst,budget=10**7,seed=0)
                rows.append({"scenario":year,"n":n,"seed":0,"algorithm":"Exact","fitness":ex["best_fitness"],
                             "runtime_s":ex["runtime"],"evals":ex["evals"]})
    raw=pd.DataFrame(rows); raw.to_csv(out/"raw"/"runs.csv",index=False)
    summary=raw.groupby(["scenario","n","algorithm"]).fitness.agg(["max","mean","std","median"]).reset_index()
    summary.to_csv(out/"tables"/"summary.csv",index=False)
    summary.rename(columns={"scenario":"skenario","algorithm":"algoritma","max":"terbaik","mean":"rata-rata",
                            "std":"simpangan baku","median":"median"}).to_markdown(out/"tables"/"summary.md",index=False)
    # Save best case route and readable route detail.
    best=max(cases,key=lambda x:x[3]["best_fitness"])
    year,n,alg,res=best
    (out/"routes"/"best_route.json").write_text(json.dumps({"scenario":year,"n":n,"algorithm":alg,**res["best_route"]},indent=2,ensure_ascii=False),encoding="utf8")
    pd.DataFrame(res["best_route"]["route"]).to_csv(out/"routes"/"best_route.csv",index=False)
    # Main comparison chart.
    plt.figure(figsize=(8,5))
    sub=raw[(raw.scenario==year)&(raw.n==n)]
    sub.boxplot(column="fitness",by="algorithm",grid=False)
    plt.suptitle(""); plt.title(f"Perbandingan fitness (skenario {year}, n={n})")
    plt.ylabel("Fitness total"); plt.xlabel("Algoritma"); plt.tight_layout()
    plt.savefig(out/"figures"/"fitness_boxplot.png",dpi=300); plt.close()
    # Geographic route scatter with visit order.
    c=coords.set_index("Provinsi"); route=res["best_route"]["route"]
    plt.figure(figsize=(9,6))
    plt.scatter(c.loc[inst.names,"lon"],c.loc[inst.names,"lat"],alpha=.45,label="Provinsi")
    depot=inst.names[inst.depot]; prev=depot
    for k,node in enumerate(route,1):
        name=node["province"]; plt.annotate(f'{k}. {name}\n{node["arrival_h"]:.1f} jam',(c.loc[name,"lon"],c.loc[name,"lat"]),fontsize=7)
        plt.annotate("",xy=(c.loc[name,"lon"],c.loc[name,"lat"]),xytext=(c.loc[prev,"lon"],c.loc[prev,"lat"]),arrowprops={"arrowstyle":"->","lw":.8})
        prev=name
    if route:
        plt.annotate("",xy=(c.loc[depot,"lon"],c.loc[depot,"lat"]),xytext=(c.loc[prev,"lon"],c.loc[prev,"lat"]),arrowprops={"arrowstyle":"->","lw":.8})
    plt.title("Rute terbaik: provinsi dan waktu kedatangan"); plt.xlabel("Bujur"); plt.ylabel("Lintang")
    plt.tight_layout(); plt.savefig(out/"figures"/"best_route_map.png",dpi=300); plt.close()
    (ROOT/"reports"/"figures_index.md").write_text("# Daftar gambar\n\n- `fitness_boxplot.png`: Distribusi fitness akhir tiap algoritma untuk instance terpilih.\n- `best_route_map.png`: Sketsa rute terbaik, urutan kunjungan, dan waktu kedatangan.\n",encoding="utf8")
    print("Selesai. Keluaran ada di results/ dan reports/.")
if __name__=="__main__": main()
