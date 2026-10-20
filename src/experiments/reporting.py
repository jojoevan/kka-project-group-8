"""Shared reporting for the province experiment and the FIRMS phase: the table writer and the
Indonesian column labels of every result table.

Each *_ID map renames the English column names of a results/tables/*.csv for its .md twin; FIRMS
tables reuse the province labels for the columns they share.
"""


def write_table(df, path_stem, rename=None, floatfmt=".4g"):
    """df as path_stem.csv (English columns, full precision) and path_stem.md (labels from rename)."""
    df.to_csv(path_stem.with_suffix(".csv"), index=False)
    shown = df.rename(columns=rename or {})
    path_stem.with_suffix(".md").write_text(shown.to_markdown(index=False, floatfmt=floatfmt) + "\n", encoding="utf8")


SUMMARY_ID = {"scenario": "skenario", "algorithm": "algoritma", "runs": "jumlah run", "best": "terbaik",
              "mean": "rata-rata", "std": "simpangan baku", "median": "median",
              "runtime_mean_s": "runtime rata-rata (s)", "evals_mean": "evaluasi rata-rata",
              "evals_to_95_mean": "evaluasi ke 95% rata-rata", "success_rate": "success rate (1%)",
              "best_known": "best-known"}
GAP_ID = {"scenario": "skenario", "algorithm": "algoritma", "exact": "optimum Exact",
          "mean_fitness": "fitness rata-rata", "gap_mean_pct": "gap rata-rata (%)", "gap_max_pct": "gap maks (%)",
          "optimal_rate": "proporsi optimal"}
INSTANCES_ID = {"scenario": "skenario", "budget": "budget evaluasi", "time_limit_h": "Batas waktu misi (jam)",
                "greedy_visited": "terkunjungi Greedy", "candidates": "node kandidat",
                "time_limit_binds": "batas waktu mengikat", "greedy_mission_time_h": "waktu misi Greedy (jam)"}
WILCOXON_ID = {"scenario": "skenario", "algorithm_a": "algoritma A", "algorithm_b": "algoritma B",
               "median_a": "median A", "median_b": "median B", "median_diff": "median selisih (A-B)",
               "wins_a": "A menang", "wins_b": "B menang", "statistic": "statistik W",
               "p_value": "p-value", "p_holm": "p-value Holm", "significant_0.05": "signifikan (0,05)"}
SCALABILITY_ID = {"scenario": "skenario", "algorithm": "algoritma", "runtime_mean_s": "runtime rata-rata (s)",
                  "runtime_std_s": "runtime simpangan baku (s)", "quality_mean_pct": "kualitas rata-rata (% best-known)",
                  "quality_std_pct": "kualitas simpangan baku (%)", "visited_mean": "node dikunjungi rata-rata"}
SENSITIVITY_ID = {"parameter": "parameter", "value": "nilai", "scenario": "skenario", "algorithm": "algoritma",
                  "runs": "jumlah run", "best": "terbaik", "mean": "rata-rata", "std": "simpangan baku",
                  "median": "median", "visited_mean": "node dikunjungi rata-rata",
                  "mission_time_mean_h": "waktu misi rata-rata (jam)", "runtime_mean_s": "runtime rata-rata (s)",
                  "quality_mean_pct": "kualitas rata-rata (% terbaik setting)"}
ABLATION_ROUTES_ID = {"variant": "varian rute", "algorithm": "algoritma",
                      "fitness_with_decay": "Prize dengan decay", "fitness_without_decay": "Prize tanpa decay",
                      "visited": "node dikunjungi", "mission_time_h": "waktu misi (jam)", "distance_km": "jarak (km)",
                      "ops_visited": "provinsi ber-data operasional dikunjungi",
                      "ops_mean_position": "urutan rata-rata provinsi ber-data operasional",
                      "ops_mean_arrival_h": "waktu tiba rata-rata provinsi ber-data operasional (jam)",
                      "prize_lost": "Prize hilang (dievaluasi dengan decay)", "prize_lost_pct": "Prize hilang (%)"}
ABLATION_ORDER_ID = {"province": "provinsi", "risk": "Risiko", "ops": "keparahan operasional (ops)",
                     "position_decay": "urutan (dengan decay)", "arrival_decay_h": "tiba (dengan decay, jam)",
                     "position_static": "urutan (tanpa decay)", "arrival_static_h": "tiba (tanpa decay, jam)",
                     "position_shift": "pergeseran urutan (tanpa - dengan)"}
CASE_STUDY_ID = {"order": "urutan", "province": "provinsi", "status": "status", "risk": "Risiko",
                 "ops": "keparahan operasional (ops)", "leg_km": "jarak dari node sebelumnya (km)",
                 "arrival_h": "tiba (jam)", "departure_h": "berangkat (jam)", "prize": "Prize"}
ABLATION_SEEDS_ID = {"algorithm": "algoritma", "seeds": "jumlah seed",
                     "decay_route_with_decay_mean": "Prize rute dengan decay (rata-rata)",
                     "static_route_with_decay_mean": "Prize rute tanpa decay, dievaluasi dengan decay (rata-rata)",
                     "prize_lost_mean": "Prize hilang rata-rata", "prize_lost_mean_pct": "Prize hilang rata-rata (%)",
                     "prize_lost_max_pct": "Prize hilang maks (%)",
                     "seeds_static_worse": "seed dengan rute tanpa decay lebih buruk"}

# --- Fase FIRMS (Klaster hotspot) ---------------------------------------------------------------------
FAMILY_ID = {"instance_family": "jenis instance", "candidates": INSTANCES_ID["candidates"]}
FIRMS_CALIBRATION_ID = {"time_limit_h": INSTANCES_ID["time_limit_h"], "visited": "klaster terkunjungi Greedy",
                        "visited_fraction": "fraksi terkunjungi"}
FIRMS_CLUSTERS_ID = {"name": "klaster", "lat": "lintang", "lon": "bujur", "hotspots": "jumlah hotspot",
                     "frp_sum": "Σ FRP (MW)", "region": "wilayah", "risk": "Risiko klaster"}
FIRMS_INSTANCES_ID = {**{c: INSTANCES_ID[c] for c in ("budget", "time_limit_h", "greedy_visited",
                                                       "greedy_mission_time_h")},
                      "hotspots": "hotspot", "frp_total": "Σ FRP total (MW)",
                      "greedy_visited_fraction": "fraksi terkunjungi Greedy"}
HC_COST_ID = {**FAMILY_ID, "scenario": SUMMARY_ID["scenario"], "budget": INSTANCES_ID["budget"],
              "neighbourhood_size": "ukuran neighbourhood HC",
              "budget_per_neighbourhood": "budget / neighbourhood (langkah penuh maks.)",
              "hc_restarts_mean": "restart HC rata-rata", "hc_steps_mean": "langkah naik HC rata-rata",
              "hc_single_start_mean": "fitness HC single-start rata-rata", "hc_fitness_mean": "fitness HC rata-rata",
              "hc_us_per_eval": "HC µs/evaluasi", "sa_us_per_eval": "SA µs/evaluasi", "ga_us_per_eval": "GA µs/evaluasi"}
SCALABILITY_COMBINED_ID = {**SCALABILITY_ID, **FAMILY_ID}
