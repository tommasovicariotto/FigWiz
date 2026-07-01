from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figwiz-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .styles import IEEE_RAL_STYLE, PublicationSize, get_publication_size


XLABEL_PLACEHOLDER = "XLABEL"
YLABEL_PLACEHOLDER = "YLABEL"


@dataclass(frozen=True)
class PublicationFigure:
    name: str
    eps_path: Path
    x_label: str
    y_label: str
    caption: str
    label: str
    size: PublicationSize


def save_publication_figure(
    x: np.ndarray,
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
    output_dir: Path,
) -> PublicationFigure:
    size = get_publication_size(figure_cfg.get("paper_size"))
    output_dir.mkdir(parents=True, exist_ok=True)

    name = str(figure_cfg["name"])
    eps_path = output_dir / f"{name}.eps"
    x_label = str(figure_cfg.get("x_label", "time [s]"))
    y_label = str(figure_cfg.get("y_label") or signal_cfg.get("unit") or "value")
    caption = str(figure_cfg.get("caption") or figure_cfg.get("title") or name.replace("_", " "))
    label = str(figure_cfg.get("label") or f"fig:{name}")

    fig, ax = plt.subplots(figsize=(size.width_in, size.height_in))
    _apply_axes_style(ax)
    _plot_signal(ax, np.asarray(x), np.asarray(signal), figure_cfg, signal_cfg)

    ax.set_xlabel(XLABEL_PLACEHOLDER)
    ax.set_ylabel(YLABEL_PLACEHOLDER)
    ax.margins(x=0)
    fig.tight_layout(pad=0.15)
    fig.savefig(eps_path, format="eps", bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)

    return PublicationFigure(
        name=name,
        eps_path=eps_path,
        x_label=x_label,
        y_label=y_label,
        caption=caption,
        label=label,
        size=size,
    )


def write_latex_snippet(figures: list[PublicationFigure], latex_path: Path, *, graphics_prefix: str = "") -> Path:
    latex_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        r"% FigWiz publication snippets.",
        r"% Requires: \usepackage{graphicx}",
        r"% Requires: \usepackage{psfrag}",
    ]
    blocks = [_latex_block(figure, graphics_prefix=graphics_prefix) for figure in figures]
    latex_path.write_text("\n".join(header) + "\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return latex_path


def _apply_axes_style(ax: Any) -> None:
    style = IEEE_RAL_STYLE
    ax.tick_params(axis="both", labelsize=style.tick_size, width=style.axis_line_width, length=2.5, pad=1.5)
    ax.grid(True, color="0.88", linewidth=style.grid_line_width)
    for spine in ax.spines.values():
        spine.set_linewidth(style.axis_line_width)


def _plot_signal(
    ax: Any,
    x: np.ndarray,
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
) -> None:
    style = IEEE_RAL_STYLE
    if signal.ndim == 1:
        ax.plot(x, signal, linewidth=style.line_width)
        return

    labels = signal_cfg.get("components")
    if not isinstance(labels, list) or len(labels) != signal.shape[1]:
        labels = [f"c{i + 1}" for i in range(signal.shape[1])]

    for index, label in enumerate(labels):
        ax.plot(x, signal[:, index], linewidth=style.line_width, label=str(label))
    legend = _legend_options(figure_cfg.get("legend", True), n_lines=signal.shape[1])
    if legend["show"]:
        ax.legend(
            fontsize=style.legend_size,
            frameon=False,
            loc=legend["location"],
            ncol=legend["columns"],
            handlelength=1.2,
            columnspacing=0.8,
        )


def _legend_options(raw_legend: Any, *, n_lines: int) -> dict[str, Any]:
    if raw_legend is False:
        return {"show": False, "columns": 1, "location": "best"}
    if raw_legend is True or raw_legend is None:
        return {"show": True, "columns": _automatic_legend_columns(n_lines), "location": "best"}

    show = bool(raw_legend.get("show", True))
    columns = raw_legend.get("columns", _automatic_legend_columns(n_lines))
    location = raw_legend.get("location", "best")
    return {"show": show, "columns": int(columns), "location": str(location)}


def _automatic_legend_columns(n_lines: int) -> int:
    if n_lines <= 1:
        return 1
    if n_lines <= 3:
        return n_lines
    return min(3, n_lines)


def _latex_block(figure: PublicationFigure, *, graphics_prefix: str) -> str:
    graphics_path = f"{graphics_prefix}{figure.eps_path.name}"
    return "\n".join(
        [
            r"\begin{figure}[t]",
            r"  \centering",
            rf"  \psfrag{{{XLABEL_PLACEHOLDER}}}[c][c]{{\footnotesize {figure.x_label}}}",
            rf"  \psfrag{{{YLABEL_PLACEHOLDER}}}[c][c]{{\footnotesize {figure.y_label}}}",
            rf"  \includegraphics[width={figure.size.include_width}]{{{graphics_path}}}",
            rf"  \caption{{{figure.caption}}}",
            rf"  \label{{{figure.label}}}",
            r"\end{figure}",
        ]
    )
