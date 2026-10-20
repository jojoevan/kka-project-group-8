"""Shared pieces of the interactive view: config, instances, saved results, glossary text, and a
recording wrapper that keeps every improving route of a solver run so it can be replayed.

Nothing here writes into the repo: data prep runs into a temporary directory and solvers are called
exactly as the experiments call them.
"""
import gzip
import json
import re
import sys
import tempfile
from dataclasses import fields
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from src.algorithms import SOLVERS  # noqa: E402
from src.config import load_config, province_instance  # noqa: E402
from src.data_prep import prepare  # noqa: E402
from src.instance import INSTANCE_SIZES, Instance  # noqa: E402
from src.numfmt import id_format  # noqa: E402

TABLES = ROOT / "results" / "tables"
ROUTES = ROOT / "results" / "routes"
RAW = ROOT / "results" / "raw"
ALGORITHMS = ("Greedy", "HC", "SA", "GA")
SCENARIOS = ("2019", "2026")
SIZES = INSTANCE_SIZES
EXACT_MAX_NODES = 6
EXACT_BUDGET = 10**7
COLORS = {"Greedy": "#7f7f7f", "HC": "#1f77b4", "SA": "#d62728", "GA": "#2ca02c", "Exact": "#9467bd"}
ALGORITHM_NAMES = {"Greedy": "Greedy (baseline)", "HC": "Steepest-Ascent Hill Climbing",
                   "SA": "Simulated Annealing", "GA": "Genetic Algorithm", "Exact": "Exact (brute force)"}

SEPARATORS = ",."  # Plotly layout.separators: decimal comma, dot thousands separator


def fmt(x, spec=".3f"):
    """Indonesian number format: decimal comma, dot thousands separator."""
    return id_format(x, spec)


@st.cache_resource
def config():
    return load_config(ROOT / "config.yaml")


@st.cache_resource
def features():
    """38-province feature table with the config's Risiko weights; data prep writes its side files
    (processed CSVs, data quality report) into a temporary directory instead of the repo."""
    cfg = config(); w = cfg["weights"]
    with tempfile.TemporaryDirectory() as tmp:
        return prepare(processed_dir=tmp, reports_dir=tmp, weights=(w["hist"], w["cur"], w["ops"]),
                       gamma=cfg["gamma"])[0]


@st.cache_resource
def coords():
    return pd.read_csv(ROOT / "data" / "external" / "province_coords.csv")


@st.cache_resource
def instance(n, scenario, g0=None, time_limit=None):
    """Province Instance as the experiments build it; g0 / time_limit override config.yaml."""
    overrides = []
    if g0 is not None: overrides.append(("decay_g0", float(g0)))
    if time_limit is not None: overrides.append(("time_limit_hours", float(time_limit)))
    return province_instance(config(), features(), coords(), n, scenario, tuple(overrides))


def experiment_budget(n):
    b = config()["evaluation_budget"]
    return int(b["small"] if n <= b["small_max_n"] else b["large"])


class RecordingInstance(Instance):
    """Instance that logs every improving permutation in evaluation order.

    Tracker calls evaluate once per counted evaluation, so the counter here follows the solver's
    evaluation count; the final details=True call of Tracker.result is not counted."""

    @classmethod
    def of(cls, inst):
        rec = cls(**{f.name: getattr(inst, f.name) for f in fields(inst)})
        rec.evals = 0; rec.best = float("-inf"); rec.snapshots = []
        return rec

    def evaluate(self, perm, details=False):
        out = super().evaluate(perm, details)
        if not details:
            self.evals += 1
            if out > self.best:
                self.best = out
                self.snapshots.append((self.evals, [int(x) for x in perm], out))
        return out


@st.cache_data(show_spinner=False, max_entries=64)
def run(algorithm, n, scenario, g0, time_limit, budget, seed):
    """One solver run on a province instance plus its improving routes [(evals, perm, fitness)]."""
    rec = RecordingInstance.of(instance(n, scenario, g0, time_limit))
    result = SOLVERS[algorithm](rec, EXACT_BUDGET if algorithm == "Exact" else budget, seed)
    result["snapshots"] = rec.snapshots
    return result


# ---------- saved results ----------

@st.cache_data
def table(name):
    return pd.read_csv(TABLES / f"{name}.csv")


@st.cache_data
def raw_runs(name="runs"):
    return pd.read_csv(RAW / f"{name}.csv")


@st.cache_data
def saved_route(name):
    return json.loads((ROUTES / f"{name}.json").read_text(encoding="utf8"))


@st.cache_data
def histories(name="histories"):
    with gzip.open(RAW / f"{name}.jsonl.gz", "rt", encoding="utf8") as f:
        return [json.loads(line) for line in f]


def best_known(scenario, n):
    s = table("summary"); row = s[(s.scenario.astype(str) == str(scenario)) & (s.n == n)]
    return float(row.best_known.iloc[0]) if len(row) else None


# ---------- documentation text ----------

@st.cache_data
def glossary():
    """GLOSSARY.md term -> definition (first paragraph), used as tooltips."""
    text = (ROOT / "GLOSSARY.md").read_text(encoding="utf8")
    return {m[1]: m[2].strip() for m in re.finditer(r"^\*\*(.+?)\*\*(?: \(`[^`]*`\))?:\n(.+)$", text, re.M)}


def term(name):
    return glossary().get(name, "")


@st.cache_data
def readme_section(title, start_marker=None, end_marker=None):
    """Text of a README '## title' section (optionally cut between two markers), AUTO comments removed."""
    text = (ROOT / "README.md").read_text(encoding="utf8")
    start = text.index(f"## {title}\n") + len(f"## {title}\n"); end = text.find("\n## ", start)
    body = text[start:end if end != -1 else None]
    if start_marker: body = body[body.index(start_marker):]
    if end_marker and end_marker in body: body = body[:body.index(end_marker)]
    return re.sub(r"<!--.*?-->\n?", "", body).strip()
