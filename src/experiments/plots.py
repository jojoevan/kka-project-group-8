"""Figures for the main comparison (Indonesian titles and labels, 300 dpi)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DPI = 300


def boxplot_fitness(runs, n, algorithms, path):
    """Final fitness over the seeds per algorithm, one panel per Skenario tahun, for instance size n."""
    sub = runs[(runs.n == n) & runs.algorithm.isin(algorithms)]
    scenarios = sorted(sub.scenario.astype(str).unique())
    fig, axes = plt.subplots(1, len(scenarios), figsize=(5.5 * len(scenarios), 4.5), squeeze=False)
    for ax, sc in zip(axes[0], scenarios):
        s = sub[sub.scenario.astype(str) == sc]
        data = [s[s.algorithm == a].fitness.to_numpy() for a in algorithms]
        ax.boxplot(data, tick_labels=algorithms, showmeans=True)
        ax.set_title(f"Skenario {sc}"); ax.set_xlabel("Algoritma"); ax.set_ylabel("Fitness akhir (total Prize)")
        ax.grid(axis="y", alpha=.3)
    seeds = sub.seed.nunique()
    fig.suptitle(f"Sebaran fitness akhir {seeds} seed per algoritma (n = {n})")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def route_map(coords, inst, route_detail, title, path):
    """Lon/lat case-study map: Depot, numbered Kunjungan with arrival-time labels and direction arrows,
    and Node dilewati marked separately (labelled with their Risiko)."""
    c = coords.set_index("Provinsi"); route = route_detail["route"]
    def xy(name): return float(c.loc[name, "lon"]), float(c.loc[name, "lat"])
    depot = inst.names[inst.depot]
    fig, ax = plt.subplots(figsize=(12, 7.5))
    stops = [depot] + [node["province"] for node in route] + ([depot] if route else [])
    for a, b in zip(stops, stops[1:]):
        ax.annotate("", xy=xy(b), xytext=xy(a),
                    arrowprops={"arrowstyle": "-|>", "lw": .9, "color": "tab:blue", "shrinkA": 5, "shrinkB": 5})
    if route:
        ax.scatter(*zip(*[xy(node["province"]) for node in route]), s=70, c="tab:blue", zorder=3,
                   label=f"Kunjungan ({len(route)})")
    for k, node in enumerate(route, 1):
        x, y = xy(node["province"])
        ax.text(x, y, str(k), color="white", fontsize=6, ha="center", va="center", zorder=4, fontweight="bold")
        ax.annotate(f'{k}. {node["province"]}\ntiba {node["arrival_h"]:.1f} jam', (x, y), xytext=(5, 4),
                    textcoords="offset points", fontsize=6.5)
    skipped = route_detail["skipped"]
    if skipped:
        ax.scatter(*zip(*[xy(s["province"]) for s in skipped]), marker="x", s=40, c="gray", zorder=3,
                   label=f"Node dilewati ({len(skipped)})")
        for s in skipped:
            ax.annotate(f'{s["province"]} (Risiko {s["risk"]:.2f})', xy(s["province"]), xytext=(4, -8),
                        textcoords="offset points", fontsize=5.5, color="gray")
    ax.scatter(*xy(depot), marker="*", s=280, c="red", zorder=5, label=f"Depot ({depot})")
    ax.set_title(f"{title}\nTotal Prize {route_detail['fitness']:.3f}; waktu misi "
                 f"{route_detail['mission_time_h']:.1f} dari {inst.time_limit:g} jam; jarak "
                 f"{route_detail['distance_km']:.0f} km", fontsize=10)
    ax.set_xlabel("Bujur (°BT)"); ax.set_ylabel("Lintang (°)"); ax.grid(alpha=.3); ax.set_aspect("equal")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def convergence(conv, n, algorithms, path):
    """Mean best-so-far fitness vs evaluations with a +-1 std band across seeds, one panel per Skenario
    tahun, for instance size n."""
    sub = conv[conv.n == n]
    scenarios = sorted(sub.scenario.astype(str).unique())
    fig, axes = plt.subplots(1, len(scenarios), figsize=(6 * len(scenarios), 4.5), squeeze=False)
    for ax, sc in zip(axes[0], scenarios):
        s = sub[sub.scenario.astype(str) == sc]
        for a in algorithms:
            c = s[s.algorithm == a].sort_values("evals")
            if c.empty: continue
            line, = ax.plot(c.evals, c["mean"], label=a, lw=1.2)
            ax.fill_between(c.evals, c["mean"] - c["std"], c["mean"] + c["std"], color=line.get_color(), alpha=.2)
        ax.set_title(f"Skenario {sc}"); ax.set_xlabel("Jumlah evaluasi fitness")
        ax.set_ylabel("Fitness terbaik sejauh ini (total Prize)"); ax.grid(alpha=.3); ax.legend(title="Algoritma")
    seeds = int(sub.seeds.max())
    fig.suptitle(f"Kurva konvergensi: rata-rata ± simpangan baku {seeds} seed (n = {n})")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def scalability(table, algorithms, path):
    """Runtime (log scale) and quality (% of best-known) against n; one column per Skenario tahun."""
    scenarios = sorted(table.scenario.astype(str).unique())
    fig, axes = plt.subplots(2, len(scenarios), figsize=(6 * len(scenarios), 8), squeeze=False)
    for col, sc in enumerate(scenarios):
        s = table[table.scenario.astype(str) == sc]
        for a in algorithms:
            c = s[s.algorithm == a].sort_values("n")
            axes[0, col].errorbar(c.n, c.runtime_mean_s, yerr=c.runtime_std_s, marker="o", capsize=3, label=a)
            axes[1, col].errorbar(c.n, c.quality_mean_pct, yerr=c.quality_std_pct, marker="o", capsize=3, label=a)
        axes[0, col].set_yscale("log"); axes[0, col].set_ylabel("Runtime rata-rata per run (detik, log)")
        axes[1, col].set_ylabel("Kualitas solusi (% dari best-known)")
        for ax in axes[:, col]:
            ax.set_title(f"Skenario {sc}"); ax.set_xlabel("Ukuran instance n (termasuk Depot)")
            ax.set_xticks(sorted(s.n.unique())); ax.grid(alpha=.3); ax.legend(title="Algoritma")
    fig.suptitle("Skalabilitas: runtime dan kualitas solusi terhadap ukuran instance")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


SENSITIVITY_LABEL = {"time_limit_hours": "Batas waktu misi T_max (jam)", "decay_g0": "Laju decay dasar g0 (per jam)"}


def sensitivity(table, algorithms, path):
    """Top row: mean fitness (+-1 std) per algorithm vs the swept value; bottom row: nodes visited.
    One column per swept parameter."""
    params = list(dict.fromkeys(table.parameter))
    fig, axes = plt.subplots(2, len(params), figsize=(6 * len(params), 8), squeeze=False)
    for col, p in enumerate(params):
        s = table[table.parameter == p]
        for a in algorithms:
            c = s[s.algorithm == a].sort_values("value")
            axes[0, col].errorbar(c.value, c["mean"], yerr=c["std"], marker="o", capsize=3, label=a)
            axes[1, col].plot(c.value, c.visited_mean, marker="o", label=a)
        axes[0, col].set_ylabel("Fitness akhir rata-rata (total Prize)")
        axes[1, col].set_ylabel("Node dikunjungi rata-rata")
        for ax in axes[:, col]:
            ax.set_xlabel(SENSITIVITY_LABEL.get(p, p)); ax.set_xticks(sorted(s.value.unique()))
            ax.grid(alpha=.3); ax.legend(title="Algoritma")
        axes[0, col].set_title(f"Sensitivitas terhadap {SENSITIVITY_LABEL.get(p, p).split(' (')[0]}")
    n, sc, seeds = int(table.n.iloc[0]), table.scenario.iloc[0], int(table.runs.max())
    fig.suptitle(f"Analisis sensitivitas (n = {n}, skenario {sc}, {seeds} seed; parameter lain tetap default)")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def boxplot_fitness_firms(runs, algorithms, path):
    """Final fitness over the seeds per algorithm, one panel per k (Klaster hotspot FIRMS)."""
    ks = sorted(runs.k.unique())
    fig, axes = plt.subplots(1, len(ks), figsize=(5 * len(ks), 4.5), squeeze=False)
    for ax, k in zip(axes[0], ks):
        s = runs[runs.k == k]
        ax.boxplot([s[s.algorithm == a].fitness.to_numpy() for a in algorithms], tick_labels=algorithms,
                   showmeans=True)
        ax.set_title(f"FIRMS k = {k}"); ax.set_xlabel("Algoritma"); ax.set_ylabel("Fitness akhir (total Prize)")
        ax.grid(axis="y", alpha=.3)
    fig.suptitle(f"Instance FIRMS: sebaran fitness akhir {runs.seed.nunique()} seed per algoritma")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def scalability_combined(table, algorithms, path, province_scenario="2026"):
    """Runtime (log) and quality against the number of candidate nodes for province instances (solid,
    one Skenario tahun) and FIRMS Klaster hotspot instances (dashed, labelled), on a log x axis."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    colors = {a: f"C{i}" for i, a in enumerate(algorithms)}
    prov = table[(table.instance_family == "provinsi") & (table.scenario.astype(str) == province_scenario)]
    firms = table[table.instance_family == "FIRMS"]
    for a in algorithms:
        for fam, sub, style, marker in ((f"provinsi {province_scenario}", prov, "-", "o"),
                                        ("FIRMS", firms, "--", "s")):
            c = sub[sub.algorithm == a].sort_values("candidates")
            if c.empty: continue
            kw = {"ls": style, "marker": marker, "capsize": 3, "color": colors[a], "label": f"{a} ({fam})"}
            axes[0].errorbar(c.candidates, c.runtime_mean_s, yerr=c.runtime_std_s, **kw)
            axes[1].errorbar(c.candidates, c.quality_mean_pct, yerr=c.quality_std_pct, **kw)
    axes[0].set_yscale("log"); axes[0].set_ylabel("Runtime rata-rata per run (detik, log)")
    axes[1].set_ylabel("Kualitas solusi (% dari best-known instance)")
    ticks = sorted(set(int(t) for t in table.candidates))
    for ax in axes:
        ax.set_xscale("log"); ax.set_xticks(ticks); ax.set_xticklabels([str(t) for t in ticks], fontsize=7)
        ax.minorticks_off(); ax.set_xlabel("Jumlah node kandidat (tanpa Depot, skala log)"); ax.grid(alpha=.3)
        if not firms.empty:
            ax.axvspan(firms.candidates.min() * .85, firms.candidates.max() * 1.15, color="orange", alpha=.1)
            ax.text(firms.candidates.min() * .87, .98, "Instance FIRMS\n(Klaster hotspot)", fontsize=8, va="top",
                    color="darkorange", transform=ax.get_xaxis_transform())
    axes[1].legend(fontsize=6.5, ncol=2, loc="lower left")
    fig.suptitle(f"Skalabilitas gabungan: instance provinsi (garis penuh, skenario {province_scenario}) "
                 "dan instance FIRMS (garis putus-putus)")
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)


def firms_cluster_map(hotspots, nodes, depot, inst, route_detail, bboxes, title, path):
    """Hotspots (grey), Klaster hotspot nodes coloured by Risiko, the best route (numbered, arrows),
    Node dilewati (hollow) and the Depot, in lon/lat."""
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.scatter(hotspots.lon, hotspots.lat, s=1, c="lightgray", alpha=.5, rasterized=True,
               label=f"Hotspot VIIRS ({len(hotspots)})")
    for name, (lat0, lat1, lon0, lon1) in bboxes.items():
        ax.add_patch(Rectangle((lon0, lat0), lon1 - lon0, lat1 - lat0, fill=False, ls=":", lw=.8, color="gray"))
        ax.text(lon0 + .1, lat1 - .1, f"Bounding box {name}", fontsize=7, va="top", color="gray")
    pos = {inst.names[inst.depot]: (depot["lon"], depot["lat"])}
    pos.update({r.name: (r.lon, r.lat) for r in nodes.itertuples()})
    route = route_detail["route"]; d = inst.names[inst.depot]
    stops = [d] + [v["province"] for v in route] + ([d] if route else [])
    for a, b in zip(stops, stops[1:]):
        ax.annotate("", xy=pos[b], xytext=pos[a],
                    arrowprops={"arrowstyle": "-|>", "lw": .7, "color": "tab:blue", "shrinkA": 3, "shrinkB": 3})
    visited = {v["province"] for v in route}
    v = nodes[nodes.name.isin(visited)]; sk = nodes[~nodes.name.isin(visited)]
    sc = ax.scatter(v.lon, v.lat, c=v.risk, cmap="YlOrRd", vmin=0, vmax=1, s=45, edgecolors="k", linewidths=.5,
                    zorder=3, label=f"Klaster dikunjungi ({len(v)})")
    ax.scatter(sk.lon, sk.lat, facecolors="none", edgecolors=plt.cm.YlOrRd(sk.risk.to_numpy()), s=30,
               linewidths=1.2, zorder=3, label=f"Node dilewati ({len(sk)})")
    for i, node in enumerate(route, 1):
        ax.annotate(str(i), pos[node["province"]], xytext=(3, 3), textcoords="offset points", fontsize=5.5)
    ax.scatter(depot["lon"], depot["lat"], marker="*", s=300, c="blue", zorder=5, label=f"Depot ({depot['name']})")
    fig.colorbar(sc, ax=ax, shrink=.7, label="Risiko klaster (Σ FRP → log1p → min-max)")
    ax.set_title(f"{title}\nTotal Prize {route_detail['fitness']:.3f}; {len(route)} Kunjungan; waktu misi "
                 f"{route_detail['mission_time_h']:.1f} dari {inst.time_limit:g} jam; jarak "
                 f"{route_detail['distance_km']:.0f} km", fontsize=10)
    ax.set_xlabel("Bujur (°BT)"); ax.set_ylabel("Lintang (°)"); ax.grid(alpha=.3); ax.set_aspect("equal")
    ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)
