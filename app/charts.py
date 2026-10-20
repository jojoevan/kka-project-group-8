"""Plotly figures for the interactive view. Maps are plain lon/lat axes with equal aspect (no basemap),
so they render without an internet connection."""
import numpy as np
import plotly.graph_objects as go

from app.core import ALGORITHMS, COLORS, SEPARATORS, fmt

MAX_FRAMES = 60


def _axes(fig, height=520):
    fig.update_xaxes(title="Bujur (°BT)", showgrid=True, gridcolor="#eee", zeroline=False)
    fig.update_yaxes(title="Lintang (°)", showgrid=True, gridcolor="#eee", zeroline=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(height=height, separators=SEPARATORS, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="#f7fbff",
                      legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0))
    return fig


def risk_map(names, lat, lon, risk, depot, ops=None, title=""):
    """All nodes coloured by Risiko, Depot as a star."""
    ops = np.zeros(len(names)) if ops is None else ops
    hover = [f"<b>{n}</b><br>Risiko {fmt(r, '.3f')}<br>ops {fmt(o, '.2f')}" for n, r, o in zip(names, risk, ops)]
    fig = go.Figure()
    fig.add_scatter(x=lon, y=lat, mode="markers", name="Node (warna = Risiko)", hovertext=hover,
                    hoverinfo="text", marker=dict(size=8 + 22 * np.asarray(risk), color=risk, colorscale="YlOrRd",
                                                  cmin=0, cmax=1, line=dict(width=.6, color="#555"),
                                                  colorbar=dict(title="Risiko", thickness=12)))
    d = names.index(depot)
    fig.add_scatter(x=[lon[d]], y=[lat[d]], mode="markers+text", name=f"Depot ({depot})", text=["Depot"],
                    textposition="top center", hoverinfo="skip",
                    marker=dict(symbol="star", size=22, color="#1f3b73", line=dict(width=1, color="white")))
    fig.update_layout(title=title)
    return _axes(fig)


def _route_traces(pos, depot, route, skipped, color):
    """Traces of one route state: flight path, numbered Kunjungan, Node dilewati, Depot."""
    stops = [depot] + [r["province"] for r in route] + ([depot] if route else [])
    xs = [pos[s][0] for s in stops]; ys = [pos[s][1] for s in stops]
    visit_hover = [f"<b>{k}. {r['province']}</b><br>tiba {fmt(r['arrival_h'], '.1f')} jam<br>"
                   f"Risiko {fmt(r['risk'], '.3f')} → Prize {fmt(r['prize'], '.3f')}"
                   for k, r in enumerate(route, 1)]
    skip_hover = [f"<b>{s['province']}</b><br>Node dilewati<br>Risiko {fmt(s['risk'], '.3f')}" for s in skipped]
    return [
        go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=2), name="Jalur terbang",
                   hoverinfo="skip"),
        go.Scatter(x=[pos[r["province"]][0] for r in route], y=[pos[r["province"]][1] for r in route],
                   mode="markers+text", text=[str(k) for k in range(1, len(route) + 1)],
                   textfont=dict(color="white", size=10), name="Kunjungan (nomor = urutan)",
                   marker=dict(size=20, color=color, line=dict(width=1, color="white")),
                   hovertext=visit_hover, hoverinfo="text"),
        go.Scatter(x=[pos[s["province"]][0] for s in skipped], y=[pos[s["province"]][1] for s in skipped],
                   mode="markers", name="Node dilewati", marker=dict(symbol="x", size=9, color="#888"),
                   hovertext=skip_hover, hoverinfo="text"),
        go.Scatter(x=[pos[depot][0]], y=[pos[depot][1]], mode="markers", name=f"Depot ({depot})",
                   marker=dict(symbol="star", size=22, color="#1f3b73", line=dict(width=1, color="white")),
                   hoverinfo="name"),
    ]


def route_map(pos, depot, states, color="#d62728", title="", background=None, height=560):
    """Route map; with several states (label, route, skipped) it gets a play button and a slider.

    pos maps node name -> (lon, lat). background is an optional (lon, lat) point cloud drawn underneath."""
    if len(states) > MAX_FRAMES:  # keep the first, the last and evenly spaced states in between
        keep = np.unique(np.linspace(0, len(states) - 1, MAX_FRAMES).round().astype(int))
        states = [states[i] for i in keep]
    base = []
    if background is not None:
        base = [go.Scattergl(x=background[0], y=background[1], mode="markers", name="Hotspot FIRMS",
                             marker=dict(size=2, color="#f4a261", opacity=.35), hoverinfo="skip")]
    label, route, skipped = states[-1]
    fig = go.Figure(data=base + _route_traces(pos, depot, route, skipped, color))
    fig.update_layout(title=title or label)
    if len(states) > 1:
        offset = len(base)
        fig.frames = [go.Frame(data=_route_traces(pos, depot, r, s, color), name=str(i),
                               traces=list(range(offset, offset + 4)), layout=dict(title=lab))
                      for i, (lab, r, s) in enumerate(states)]
        fig.update_layout(
            updatemenus=[dict(type="buttons", direction="left", x=0, y=-.08, xanchor="left", yanchor="top",
                              buttons=[dict(label="▶ Putar", method="animate",
                                            args=[None, dict(frame=dict(duration=250, redraw=True),
                                                             transition=dict(duration=0), fromcurrent=True)]),
                                       dict(label="❚❚ Jeda", method="animate",
                                            args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
            sliders=[dict(active=len(states) - 1, x=.15, len=.85, y=-.04, currentvalue=dict(prefix="Rute ke-"),
                          steps=[dict(label=str(i + 1), method="animate",
                                      args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                                 for i in range(len(states))])])
        height += 60
    return _axes(fig, height)


def convergence(series, title="", log_x=True, band=None):
    """series: algorithm -> (evals, best-so-far fitness); band: algorithm -> std (same length)."""
    fig = go.Figure()
    for alg, (x, y) in series.items():
        c = COLORS.get(alg, "#333")
        if band and alg in band:
            sd = np.asarray(band[alg]); yy = np.asarray(y)
            fig.add_scatter(x=list(x) + list(x)[::-1], y=list(yy + sd) + list(yy - sd)[::-1], fill="toself",
                            fillcolor=c, opacity=.15, line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=x, y=y, mode="lines", name=alg, line=dict(color=c, width=2, shape="hv"))
    fig.update_xaxes(title="Evaluasi fitness yang sudah dipakai", type="log" if log_x else "linear")
    fig.update_yaxes(title="Fitness terbaik sejauh ini")
    fig.update_layout(title=title, separators=SEPARATORS, height=400, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified")
    return fig


def prize_decay(t_max, g0, kappa, risk, ops_values):
    """Prize = Risiko · exp(−g0 (1 + κ·ops) t) for a few ops values."""
    t = np.linspace(0, t_max, 200); fig = go.Figure()
    for ops in ops_values:
        g = g0 * (1 + kappa * ops)
        fig.add_scatter(x=t, y=risk * np.exp(-g * t), mode="lines",
                        name=f"ops = {fmt(ops, '.1f')} (g = {fmt(g, '.4f')})")
    fig.add_hline(y=risk, line=dict(dash="dot", color="#999"), annotation_text="Risiko (tiba di jam 0)")
    fig.update_xaxes(title="Waktu tiba (jam sejak berangkat dari Depot)")
    fig.update_yaxes(title="Prize yang didapat", range=[0, risk * 1.08])
    fig.update_layout(height=380, separators=SEPARATORS, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified")
    return fig


def boxplot(df, value="fitness", by="algorithm", title="", reference=None):
    fig = go.Figure()
    for alg in [a for a in ALGORITHMS if a in set(df[by])]:
        fig.add_box(y=df.loc[df[by] == alg, value], name=alg, marker_color=COLORS[alg], boxpoints="all",
                    jitter=.4, pointpos=0)
    if reference is not None:
        fig.add_hline(y=reference, line=dict(dash="dash", color="#333"), annotation_text="Best-known")
    fig.update_yaxes(title="Fitness (total Prize)")
    fig.update_layout(title=title, separators=SEPARATORS, height=400, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    return fig


def lines(df, x, y, group, x_title, y_title, title="", log_x=False):
    fig = go.Figure()
    for alg in [a for a in ALGORITHMS if a in set(df[group])]:
        d = df[df[group] == alg].sort_values(x)
        fig.add_scatter(x=d[x], y=d[y], mode="lines+markers", name=alg, line=dict(color=COLORS[alg], width=2))
    fig.update_xaxes(title=x_title, type="log" if log_x else "linear")
    fig.update_yaxes(title=y_title)
    fig.update_layout(title=title, separators=SEPARATORS, height=380, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified")
    return fig
