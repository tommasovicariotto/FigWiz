from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go


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

    title = figure_cfg.get("title", figure_cfg.get("name", "paperfig"))
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


def save_or_show(fig: go.Figure, output_path: str | Path, open_browser: bool = True) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="cdn", auto_open=open_browser)
    return output_path
