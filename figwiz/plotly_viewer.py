from __future__ import annotations

import html
import webbrowser
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go

from .processing import sample_time_axis


def _component_labels(signal_cfg: dict[str, Any], n_cols: int) -> list[str]:
    labels = signal_cfg.get("components")
    if labels and len(labels) == n_cols:
        return [str(x) for x in labels]
    return [f"c{i+1}" for i in range(n_cols)]


def make_timeseries_figure(
    time: np.ndarray,
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
) -> go.Figure:
    fig = go.Figure()
    signal = np.asarray(signal)

    title = figure_cfg.get("title", figure_cfg.get("name", "FigWiz"))
    y_label = figure_cfg.get("y_label") or signal_cfg.get("unit") or "value"
    x_label = figure_cfg.get("x_label", "time [s]")

    if signal.ndim == 1:
        fig.add_trace(go.Scatter(x=time, y=signal, mode="lines", name=figure_cfg.get("name", "signal")))
    else:
        labels = _component_labels(signal_cfg, signal.shape[1])
        for i, label in enumerate(labels):
            fig.add_trace(go.Scatter(x=time, y=signal[:, i], mode="lines", name=label))

    events = figure_cfg.get("events", [])
    for event in events:
        x = event.get("time")
        label = event.get("label", "event")
        if x is not None:
            fig.add_vline(x=float(x), line_dash="dash", annotation_text=label, annotation_position="top")

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def make_array_figure(
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
    fs: float,
) -> go.Figure:
    fig = go.Figure()
    signal = np.asarray(signal)

    title = figure_cfg.get("title", figure_cfg.get("name", "FigWiz"))
    y_label = figure_cfg.get("y_label") or signal_cfg.get("unit") or "value"
    x_label = figure_cfg.get("x_label", "time [s]")
    x = sample_time_axis(signal.shape[0], fs)

    if signal.ndim == 1:
        fig.add_trace(go.Scatter(x=x, y=signal, mode="lines", name=figure_cfg.get("name", "signal")))
    else:
        labels = _component_labels(signal_cfg, signal.shape[1])
        for i, label in enumerate(labels):
            fig.add_trace(go.Scatter(x=x, y=signal[:, i], mode="lines", name=label))

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def save_or_show(fig: go.Figure, output_path: str | Path, open_browser: bool = True) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="cdn", auto_open=open_browser)
    return output_path


def save_dashboard(
    figures: list[tuple[str, go.Figure]],
    output_path: str | Path,
    *,
    open_browser: bool = True,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    panels = []
    for index, (name, fig) in enumerate(figures):
        include_plotlyjs: str | bool = "cdn" if index == 0 else False
        figure_html = fig.to_html(full_html=False, include_plotlyjs=include_plotlyjs)
        panels.append(f'<section class="plot-panel" aria-label="{html.escape(name)}">{figure_html}</section>')

    output_path.write_text(_dashboard_html("\n".join(panels), count=len(figures)), encoding="utf-8")
    if open_browser:
        webbrowser.open(output_path.resolve().as_uri())
    return output_path


def _dashboard_html(body: str, *, count: int) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FigWiz figures</title>
  <style>
    html,
    body {{
      margin: 0;
      min-height: 100%;
      background: #ffffff;
      font-family: Arial, sans-serif;
    }}
    .plot-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(520px, 100%), 1fr));
      gap: 12px;
      padding: 12px;
      box-sizing: border-box;
      min-height: 100vh;
    }}
    .plot-panel {{
      min-height: 420px;
      height: calc(100vh - 24px);
      border: 1px solid #d8dde6;
      box-sizing: border-box;
      overflow: hidden;
    }}
    .plot-grid.count-4 .plot-panel,
    .plot-grid.count-5 .plot-panel,
    .plot-grid.count-6 .plot-panel {{
      height: calc((100vh - 36px) / 2);
    }}
    @media (min-width: 1600px) {{
      .plot-grid.count-5 .plot-panel:first-child {{
        grid-column: span 2;
      }}
    }}
    .plot-panel .plotly-graph-div {{
      height: 100% !important;
      width: 100% !important;
    }}
    @media (max-width: 720px) {{
      .plot-panel {{
        height: 420px;
      }}
    }}
  </style>
</head>
<body>
  <main class="plot-grid count-{count}">
    {body}
  </main>
</body>
</html>
"""
