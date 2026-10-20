"""Plotly figures for the interactive view. Maps are plain lon/lat axes with equal aspect (no basemap),
so they render without an internet connection."""
import numpy as np
import plotly.graph_objects as go

from app.core import ALGORITHMS, COLORS, SEPARATORS, fmt

MAX_FRAMES = 60
FONT = "Source Sans, sans-serif"  # the font Streamlit loads for the page
GRID = "#e6e8eb"
AXIS = "#c9ced4"
TITLE_ROW, LEGEND_ROW = 24, 30  # px reserved above the plot area per title line / for the legend row


def finish(fig, height=400, title=None, legend=True, bottom=10):
    """Shared look: title at the top left, legend in its own row between the title and the plot, so the two
    never overlap; the top margin grows with the number of title lines."""
    lines = title.count("<br>") + 1 if title else 0
    top = 12 + TITLE_ROW * lines + (LEGEND_ROW if legend else 0)
    fig.update_layout(
        height=height, separators=SEPARATORS, font=dict(family=FONT, size=13, color="#1f2933"),
        margin=dict(l=10, r=10, t=top, b=bottom), plot_bgcolor="white", paper_bgcolor="white",
        showlegend=legend,
        legend=dict(orientation="h", x=0, xanchor="left", y=1, yanchor="bottom", yref="paper",
                    font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="white"))
    if title:
        fig.update_layout(title=dict(text=title, x=0, xref="paper", xanchor="left", y=1, yref="container",
                                     yanchor="top", pad=dict(t=10), font=dict(size=15)))
    axis = dict(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=AXIS, ticks="outside", tickcolor=AXIS,
                title_standoff=8)
    fig.update_xaxes(**axis); fig.update_yaxes(**axis)
    return fig


def _map_axes(fig, lon, lat, pad=1.5):
    """Lon/lat axes with equal aspect around the data plus a small margin. The axis ranges stretch to fill
    the plot area (constrain="range"), so a wide map never leaves empty bands above and below it."""
    lon = np.asarray(lon, float); lat = np.asarray(lat, float)
    fig.update_xaxes(title="Bujur (°BT)", range=[lon.min() - pad, lon.max() + pad], constrain="range")
    fig.update_yaxes(title="Lintang (°)", range=[lat.min() - pad, lat.max() + pad],
                     scaleanchor="x", scaleratio=1, constrain="range")
    return fig


def risk_map(names, lat, lon, risk, depot, ops=None, title=None, height=460):
    """All nodes coloured by Risiko, Depot as a star."""
    ops = np.zeros(len(names)) if ops is None else ops
    hover = [f"<b>{n}</b><br>Risiko {fmt(r, '.3f')}<br>ops {fmt(o, '.2f')}" for n, r, o in zip(names, risk, ops)]
    fig = go.Figure()
    fig.add_scatter(x=lon, y=lat, mode="markers", name="Provinsi (warna dan ukuran = Risiko)", hovertext=hover,
                    hoverinfo="text", marker=dict(size=8 + 22 * np.asarray(risk), color=risk, colorscale="YlOrRd",
                                                  cmin=0, cmax=1, line=dict(width=.6, color="#555"),
                                                  colorbar=dict(title="Risiko", thickness=12, len=.8)))
    d = names.index(depot)
    fig.add_scatter(x=[lon[d]], y=[lat[d]], mode="markers", name=f"Depot ({depot})", hoverinfo="name",
                    marker=dict(symbol="star", size=20, color="#1f3b73", line=dict(width=1, color="white")))
    finish(fig, height, title)
    return _map_axes(fig, lon, lat)


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
                   textfont=dict(color="white", size=10), name="Kunjungan (nomor urut)",
                   marker=dict(size=20, color=color, line=dict(width=1, color="white")),
                   hovertext=visit_hover, hoverinfo="text"),
        go.Scatter(x=[pos[s["province"]][0] for s in skipped], y=[pos[s["province"]][1] for s in skipped],
                   mode="markers", name="Node dilewati", marker=dict(symbol="x", size=9, color="#8a9099"),
                   hovertext=skip_hover, hoverinfo="text"),
        go.Scatter(x=[pos[depot][0]], y=[pos[depot][1]], mode="markers", name="Depot",
                   marker=dict(symbol="star", size=20, color="#1f3b73", line=dict(width=1, color="white")),
                   hoverinfo="name"),
    ]


def route_map(pos, depot, states, color="#d62728", title=None, background=None, height=520):
    """Route map; with several states (label, route, skipped) it gets a play button and a slider whose
    current value shows the state's label, so the title above stays fixed.

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
    bottom = 10
    if len(states) > 1:
        offset = len(base)
        fig.frames = [go.Frame(data=_route_traces(pos, depot, r, s, color), name=str(i),
                               traces=list(range(offset, offset + 4))) for i, (_, r, s) in enumerate(states)]
        fig.update_layout(
            updatemenus=[dict(type="buttons", direction="left", x=0, xanchor="left", y=0, yanchor="top",
                              pad=dict(t=0, l=0), showactive=False,
                              buttons=[dict(label="Putar", method="animate",
                                            args=[None, dict(frame=dict(duration=300, redraw=True),
                                                             transition=dict(duration=0), fromcurrent=True)]),
                                       dict(label="Jeda", method="animate",
                                            args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
            sliders=[dict(active=len(states) - 1, x=.16, len=.84, y=0, yanchor="top", pad=dict(t=0, b=0), ticklen=0, font=dict(size=1, color="rgba(0,0,0,0)"),
                          currentvalue=dict(prefix="", xanchor="left", font=dict(size=13, color="#1f2933")),
                          steps=[dict(label=lab, method="animate",
                                      args=[[str(i)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                                 for i, (lab, _, _) in enumerate(states)])])
        bottom = 120
    elif label:
        title = f"{title}<br>{label}" if title else label
    shown = {depot} | {v["province"] for _, r, s in states for v in [*r, *s]}
    xs = [pos[n][0] for n in shown]; ys = [pos[n][1] for n in shown]
    finish(fig, height + bottom, title, bottom=bottom)
    if len(states) > 1:  # controls sit in the bottom margin, below the axis title (paper coordinates)
        y = -56 / (height - fig.layout.margin.t)
        fig.layout.updatemenus[0].y = y; fig.layout.sliders[0].y = y
    return _map_axes(fig, xs, ys)


def convergence(series, title=None, log_x=True, band=None, height=400):
    """series: algorithm -> (evals, best-so-far fitness); band: algorithm -> std (same length)."""
    fig = go.Figure()
    for alg, (x, y) in series.items():
        c = COLORS.get(alg, "#333")
        if band and alg in band:
            sd = np.asarray(band[alg]); yy = np.asarray(y)
            fig.add_scatter(x=list(x) + list(x)[::-1], y=list(yy + sd) + list(yy - sd)[::-1], fill="toself",
                            fillcolor=c, opacity=.15, line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=x, y=y, mode="lines", name=alg, line=dict(color=c, width=2, shape="hv"))
    finish(fig, height, title)
    fig.update_xaxes(title="Evaluasi fitness yang sudah dipakai", type="log" if log_x else "linear")
    fig.update_yaxes(title="Fitness terbaik sejauh ini")
    fig.update_layout(hovermode="x unified")
    return fig


def prize_decay(t_max, g0, kappa, risk, ops_values, height=380):
    """Prize = Risiko · exp(−g0 (1 + κ·ops) t) for a few ops values."""
    t = np.linspace(0, t_max, 200); fig = go.Figure()
    for ops, color in zip(ops_values, ("#2b6cb0", "#dd8a3e", "#b7412e")):
        g = g0 * (1 + kappa * ops)
        fig.add_scatter(x=t, y=risk * np.exp(-g * t), mode="lines", line=dict(color=color, width=2.5),
                        name=f"ops = {fmt(ops, '.1f')} (g = {fmt(g, '.4f')})")
    fig.add_hline(y=risk, line=dict(dash="dot", color="#999"), annotation_text="Risiko (tiba di jam 0)",
                  annotation_position="bottom right")
    finish(fig, height)
    fig.update_xaxes(title="Waktu tiba (jam sejak berangkat dari Depot)")
    fig.update_yaxes(title="Prize yang didapat", range=[0, risk * 1.08])
    fig.update_layout(hovermode="x unified")
    return fig


def boxplot(df, value="fitness", by="algorithm", title=None, reference=None, height=400):
    fig = go.Figure()
    for alg in [a for a in ALGORITHMS if a in set(df[by])]:
        fig.add_box(y=df.loc[df[by] == alg, value], name=alg, marker_color=COLORS[alg], boxpoints="all",
                    jitter=.4, pointpos=0)
    if reference is not None:
        fig.add_hline(y=reference, line=dict(dash="dash", color="#333"), annotation_text="Best-known",
                      annotation_position="top left")
    finish(fig, height, title, legend=False)
    fig.update_yaxes(title="Fitness (total Prize)")
    fig.update_xaxes(showgrid=False)
    return fig


def lines(df, x, y, group, x_title, y_title, title=None, log_x=False, height=380):
    """One line per algorithm; the x ticks are exactly the measured x values."""
    fig = go.Figure()
    for alg in [a for a in ALGORITHMS if a in set(df[group])]:
        d = df[df[group] == alg].sort_values(x)
        fig.add_scatter(x=d[x], y=d[y], mode="lines+markers", name=alg, line=dict(color=COLORS[alg], width=2))
    finish(fig, height, title)
    ticks = sorted(set(df[x]))
    fig.update_xaxes(title=x_title, type="log" if log_x else "linear", tickvals=ticks,
                     ticktext=[fmt(v, "g") for v in ticks])
    fig.update_yaxes(title=y_title)
    fig.update_layout(hovermode="x unified")
    return fig


def dumbbell(labels, a, b, a_name, b_name, x_title, title=None, a_color="#b7412e", b_color="#8a9099", height=None):
    """Two values per label on one horizontal line (e.g. visit position with and without decay)."""
    height = height or 140 + 36 * len(labels)
    fig = go.Figure()
    for lab, va, vb in zip(labels, a, b):
        fig.add_scatter(x=[va, vb], y=[lab, lab], mode="lines", line=dict(color=AXIS, width=3),
                        showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=a, y=labels, mode="markers", name=a_name, marker=dict(size=13, color=a_color))
    fig.add_scatter(x=b, y=labels, mode="markers", name=b_name, marker=dict(size=13, color=b_color))
    finish(fig, height, title)
    fig.update_xaxes(title=x_title)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def bars(x, y, colors, text, y_title, title=None, height=400):
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=colors, text=text, textposition="outside", cliponaxis=False))
    finish(fig, height, title, legend=False)
    fig.update_yaxes(title=y_title, range=[0, max(y) * 1.18])
    fig.update_xaxes(showgrid=False)
    return fig


def line(x, y, color, x_title, y_title, title=None, log_y=False, height=300):
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=2)))
    finish(fig, height, title, legend=False)
    fig.update_xaxes(title=x_title)
    fig.update_yaxes(title=y_title, type="log" if log_y else "linear")
    return fig
