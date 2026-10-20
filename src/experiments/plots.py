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
    """Lon/lat sketch of a route with visit order and arrival times."""
    c = coords.set_index("Provinsi"); route = route_detail["route"]
    fig = plt.figure(figsize=(9, 6))
    plt.scatter(c.loc[inst.names, "lon"], c.loc[inst.names, "lat"], alpha=.45, label="Provinsi")
    depot = inst.names[inst.depot]; prev = depot
    plt.scatter([c.loc[depot, "lon"]], [c.loc[depot, "lat"]], marker="*", s=150, c="red", label="Depot")
    for k, node in enumerate(route, 1):
        name = node["province"]
        plt.annotate(f'{k}. {name}\n{node["arrival_h"]:.1f} jam', (c.loc[name, "lon"], c.loc[name, "lat"]), fontsize=7)
        plt.annotate("", xy=(c.loc[name, "lon"], c.loc[name, "lat"]), xytext=(c.loc[prev, "lon"], c.loc[prev, "lat"]),
                     arrowprops={"arrowstyle": "->", "lw": .8})
        prev = name
    if route:
        plt.annotate("", xy=(c.loc[depot, "lon"], c.loc[depot, "lat"]), xytext=(c.loc[prev, "lon"], c.loc[prev, "lat"]),
                     arrowprops={"arrowstyle": "->", "lw": .8})
    plt.title(title); plt.xlabel("Bujur"); plt.ylabel("Lintang"); plt.legend(loc="lower left")
    plt.tight_layout(); fig.savefig(path, dpi=DPI); plt.close(fig)
