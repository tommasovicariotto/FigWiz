from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figwiz-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .styles import IEEE_RAL_STYLE, REPORT_SIZE, REPORT_STYLE, PublicationSize, PublicationStyle, get_publication_size


XLABEL_PLACEHOLDER = "tim"
YLABEL_PLACEHOLDER = "ylab"
GENERIC_LEGEND_PLACEHOLDERS = ("A", "B", "C", "D", "E", "F", "G", "H")
POSITION_LEGEND_PLACEHOLDERS = ("x", "y", "z")
ROTATION_LEGEND_PLACEHOLDERS = ("a", "b", "c")


@dataclass(frozen=True)
class PublicationFigure:
    name: str
    eps_path: Path
    x_label: str
    y_label: str
    caption: str
    label: str
    size: PublicationSize
    psfrag_replacements: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class PgfplotsFigure:
    name: str
    tex_path: Path
    data_path: Path
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
    x_label = _capitalize_label(str(figure_cfg.get("x_label", "time [s]")))
    y_label = _capitalize_label(str(figure_cfg.get("y_label") or signal_cfg.get("unit") or "value"))
    caption = str(figure_cfg.get("caption") or figure_cfg.get("title") or name.replace("_", " "))
    label = str(figure_cfg.get("label") or f"fig:{name}")

    signal = np.asarray(signal)
    legend_placeholders = _legend_psfrag_replacements(signal, signal_cfg, figure_cfg)
    eps_signal_cfg = dict(signal_cfg)
    if legend_placeholders:
        eps_signal_cfg["components"] = [placeholder for placeholder, _ in legend_placeholders]

    fig, ax = plt.subplots(figsize=(size.width_in, size.height_in))
    _apply_axes_style(ax, IEEE_RAL_STYLE)
    _plot_signal(ax, np.asarray(x), signal, figure_cfg, eps_signal_cfg, IEEE_RAL_STYLE)

    ax.set_xlabel(XLABEL_PLACEHOLDER)
    ax.set_ylabel(YLABEL_PLACEHOLDER)
    ax.margins(x=0)
    fig.tight_layout(pad=0.15)
    fig.savefig(eps_path, format="eps", bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)
    psfrag_replacements = (
        (XLABEL_PLACEHOLDER, x_label),
        (YLABEL_PLACEHOLDER, y_label),
        *legend_placeholders,
    )
    _make_psfrag_placeholders_literal(eps_path, [placeholder for placeholder, _ in psfrag_replacements])

    return PublicationFigure(
        name=name,
        eps_path=eps_path,
        x_label=x_label,
        y_label=y_label,
        caption=caption,
        label=label,
        size=size,
        psfrag_replacements=psfrag_replacements,
    )


def save_pgfplots_figure(
    x: np.ndarray,
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
    tex_dir: Path,
    data_dir: Path,
    *,
    buckets_per_second: float = 10.0,
) -> PgfplotsFigure:
    size = get_publication_size(figure_cfg.get("paper_size"))
    tex_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    name = str(figure_cfg["name"])
    x_label = _capitalize_label(str(figure_cfg.get("x_label", "time [s]")))
    y_label = _capitalize_label(str(figure_cfg.get("y_label") or signal_cfg.get("unit") or "value"))
    caption = str(figure_cfg.get("caption") or figure_cfg.get("title") or name.replace("_", " "))
    label = str(figure_cfg.get("label") or f"fig:{name}")

    x_m4, signal_m4 = m4_downsample(np.asarray(x), np.asarray(signal), buckets_per_second=buckets_per_second)
    x_plot, x_axis_max = _pgfplots_time_axis(x_m4, figure_cfg)
    column_labels = _pgfplot_column_labels(signal_m4, signal_cfg)
    legend_labels = _pgfplot_legend_labels(signal_m4, signal_cfg)

    data_path = data_dir / f"{name}.dat"
    tex_path = tex_dir / f"{name}.tex"
    _write_pgfplots_data(data_path, x_plot, signal_m4, column_labels)
    _write_pgfplots_tex(
        tex_path,
        f"dat/{data_path.name}",
        x_plot,
        x_axis_max,
        signal_m4,
        column_labels,
        legend_labels,
        figure_cfg,
        x_label,
        y_label,
        size,
    )

    return PgfplotsFigure(
        name=name,
        tex_path=tex_path,
        data_path=data_path,
        x_label=x_label,
        y_label=y_label,
        caption=caption,
        label=label,
        size=size,
    )


def save_report_figure(
    x: np.ndarray,
    signal: np.ndarray,
    figure_cfg: dict[str, Any],
    signal_cfg: dict[str, Any],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    name = str(figure_cfg["name"])
    pdf_path = output_dir / f"{name}.pdf"
    x_label = _capitalize_label(str(figure_cfg.get("x_label", "time [s]")))
    y_label = _capitalize_label(str(figure_cfg.get("y_label") or signal_cfg.get("unit") or "value"))

    fig, ax = plt.subplots(figsize=(REPORT_SIZE.width_in, REPORT_SIZE.height_in))
    _apply_axes_style(ax, REPORT_STYLE)
    _plot_signal(ax, np.asarray(x), np.asarray(signal), figure_cfg, signal_cfg, REPORT_STYLE)

    ax.set_xlabel(x_label, fontsize=REPORT_STYLE.label_size)
    ax.set_ylabel(y_label, fontsize=REPORT_STYLE.label_size)
    ax.margins(x=0)
    fig.tight_layout(pad=0.45)
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    return pdf_path


def write_latex_snippet(figures: list[PublicationFigure], latex_path: Path, *, graphics_prefix: str = "") -> Path:
    latex_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        r"% FigWiz publication snippets.",
        r"\usepackage{graphicx}",
        r"\usepackage{psfrag}",
        r"\newcommand{\FontFigS}{.8}",
        r"\newcommand{\FontFigM}{1}",
    ]
    blocks = [_latex_block(figure, graphics_prefix=graphics_prefix) for figure in figures]
    latex_path.write_text("\n".join(header) + "\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return latex_path


def write_pgfplots_snippet(figures: list[PgfplotsFigure], latex_path: Path, *, input_prefix: str = "pgfplots/") -> Path:
    latex_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        r"\usepackage{tikz}",
        r"\usepackage{pgfplots}",
        r"\pgfplotsset{compat=1.18}",
        "",
        _pgfplots_style(),
    ]
    blocks = [_pgfplots_latex_block(figure, input_prefix=input_prefix) for figure in figures]
    latex_path.write_text("\n".join(header) + "\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return latex_path


def m4_downsample(
    time: np.ndarray,
    signal: np.ndarray,
    *,
    buckets_per_second: float,
) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(time).squeeze()
    signal = np.asarray(signal)
    if time.ndim != 1:
        raise ValueError("time must be 1D.")
    if time.size == 0 or buckets_per_second <= 0:
        return time, signal
    if signal.shape[0] != time.shape[0]:
        raise ValueError("signal length must match time length.")

    if time.size <= 2:
        return time, signal

    values = signal.reshape(signal.shape[0], -1)
    bucket_ids = np.floor((time - time[0]) * buckets_per_second).astype(np.int64)
    keep: set[int] = set()

    for bucket_id in np.unique(bucket_ids):
        indices = np.flatnonzero(bucket_ids == bucket_id)
        if indices.size == 0:
            continue
        keep.add(int(indices[0]))
        keep.add(int(indices[-1]))
        bucket_values = values[indices]
        for column in range(bucket_values.shape[1]):
            keep.add(int(indices[int(np.argmin(bucket_values[:, column]))]))
            keep.add(int(indices[int(np.argmax(bucket_values[:, column]))]))

    ordered = np.array(sorted(keep), dtype=int)
    return time[ordered], signal[ordered]


def _apply_axes_style(ax: Any, style: PublicationStyle) -> None:
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
    style: PublicationStyle,
) -> None:
    if signal.ndim == 1:
        ax.plot(x, signal, linewidth=style.line_width)
        return

    labels = _component_labels(signal, signal_cfg)

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
    replacements = figure.psfrag_replacements or (
        (XLABEL_PLACEHOLDER, _capitalize_label(figure.x_label)),
        (YLABEL_PLACEHOLDER, _capitalize_label(figure.y_label)),
    )
    psfrag_lines = [
        rf"  \psfrag{{{placeholder}}}[cc][cc][\FontFigS]{{{_latex_label(replacement)}}}"
        for placeholder, replacement in replacements
    ]
    return "\n".join(
        [
            r"\begin{figure}[t]",
            r"  \centering",
            *psfrag_lines,
            rf"  \includegraphics[width={figure.size.include_width}]{{{graphics_path}}}",
            rf"  \caption{{{figure.caption}}}",
            rf"  \label{{{figure.label}}}",
            r"\end{figure}",
        ]
    )


def _make_psfrag_placeholders_literal(eps_path: Path, placeholders: list[str]) -> None:
    text = eps_path.read_text(encoding="latin-1")
    for placeholder in placeholders:
        text = _replace_glyphshow_word(text, placeholder)
    eps_path.write_text(text, encoding="latin-1")


def _legend_psfrag_replacements(
    signal: np.ndarray,
    signal_cfg: dict[str, Any],
    figure_cfg: dict[str, Any],
) -> tuple[tuple[str, str], ...]:
    if signal.ndim == 1:
        return ()
    legend = _legend_options(figure_cfg.get("legend", True), n_lines=signal.shape[1])
    if not legend["show"]:
        return ()
    labels = _component_labels(signal, signal_cfg)
    placeholders = _legend_placeholders(labels)
    return tuple(zip(placeholders, labels))


def _component_labels(signal: np.ndarray, signal_cfg: dict[str, Any]) -> list[str]:
    labels = signal_cfg.get("components")
    if not isinstance(labels, list) or len(labels) != signal.shape[1]:
        return [f"c{i + 1}" for i in range(signal.shape[1])]
    return [str(label) for label in labels]


def _legend_placeholders(labels: list[str]) -> tuple[str, ...]:
    if labels == ["x", "y", "z"]:
        return POSITION_LEGEND_PLACEHOLDERS
    if labels == [r"$\alpha$", r"$\beta$", r"$\gamma$"]:
        return ROTATION_LEGEND_PLACEHOLDERS
    return GENERIC_LEGEND_PLACEHOLDERS[: len(labels)]


def _replace_glyphshow_word(text: str, word: str) -> str:
    glyph_lines = [
        rf"[-+]?\d+(?:\.\d+)? 0 m /{re.escape(letter)} glyphshow"
        for letter in word
    ]
    pattern = "\n".join(glyph_lines)
    replacement = "\n".join(
        [
            "/Helvetica findfont 10 scalefont setfont",
            rf"0 0 m ({word}) show",
        ]
    )
    return re.sub(pattern, replacement, text)


def _pgfplot_column_labels(signal: np.ndarray, signal_cfg: dict[str, Any]) -> list[str]:
    if signal.ndim == 1:
        return ["value"]

    labels = signal_cfg.get("components")
    if not isinstance(labels, list) or len(labels) != signal.shape[1]:
        labels = [f"c{i + 1}" for i in range(signal.shape[1])]
    return [_safe_pgf_column_name(str(label), fallback=f"c{index + 1}") for index, label in enumerate(labels)]


def _pgfplot_legend_labels(signal: np.ndarray, signal_cfg: dict[str, Any]) -> list[str]:
    if signal.ndim == 1:
        return ["value"]

    labels = signal_cfg.get("components")
    if not isinstance(labels, list) or len(labels) != signal.shape[1]:
        labels = [f"c{i + 1}" for i in range(signal.shape[1])]
    return [str(label) for label in labels]


def _safe_pgf_column_name(label: str, *, fallback: str) -> str:
    safe = "".join(char if char.isalnum() or char == "_" else "_" for char in label.strip())
    safe = safe.strip("_")
    if not safe:
        return fallback
    if safe[0].isdigit():
        return f"c_{safe}"
    return safe


def _write_pgfplots_data(data_path: Path, x: np.ndarray, signal: np.ndarray, column_labels: list[str]) -> None:
    signal = np.asarray(signal)
    if signal.ndim == 1:
        values = signal.reshape(-1, 1)
    else:
        values = signal
    table = np.column_stack([x, values])
    header = "time " + " ".join(column_labels)
    np.savetxt(data_path, table, header=header, comments="", fmt="%.12g")


def _write_pgfplots_tex(
    tex_path: Path,
    data_path: str,
    x: np.ndarray,
    x_axis_max: float,
    signal: np.ndarray,
    column_labels: list[str],
    legend_labels: list[str],
    figure_cfg: dict[str, Any],
    x_label: str,
    y_label: str,
    size: PublicationSize,
) -> None:
    legend = _legend_options(figure_cfg.get("legend", True), n_lines=len(column_labels))
    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"  figwiz_ieee,",
        rf"  width={size.include_width},",
        rf"  height={_pgfplots_height(size)},",
        rf"  xlabel={{{_latex_escape(x_label)}}},",
        rf"  ylabel={{{_latex_escape(y_label)}}},",
        r"  enlarge x limits=false,",
        r"  xmin=0,",
        rf"  xmax={_pgf_number(x_axis_max)},",
    ]
    final_tick = _pgfplots_integer_final_tick(x_axis_max)
    if final_tick is not None:
        lines.append(rf"  extra x ticks={{{final_tick}}},")
    if not legend["show"]:
        lines.append(r"  hide legend,")
    else:
        lines.append(rf"  legend pos={_pgfplots_best_legend_pos(x, signal)},")
        if legend["columns"] > 1:
            lines.append(rf"  legend columns={legend['columns']},")
    lines.extend(
        [
            r"]",
            *[
                item
                for column, legend_label in zip(column_labels, legend_labels)
                for item in (
                    rf"\addplot table[x=time,y={column}]{{{data_path}}};",
                    rf"\addlegendentry{{{_latex_label(legend_label)}}}",
                    "",
                )
            ],
            r"\end{axis}",
            r"\end{tikzpicture}",
        ]
    )
    tex_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _pgfplots_style() -> str:
    style = IEEE_RAL_STYLE
    return "\n".join(
        [
            r"\pgfplotsset{",
            r"  figwiz_ieee/.style={",
            r"    grid=both,",
            r"    tick align=outside,",
            r"    line width=0.18pt,",
            r"    every axis plot/.append style={mark=none},",
            rf"    tick label style={{font=\fontsize{{{style.tick_size}}}{{{style.tick_size + 1}}}\selectfont}},",
            rf"    label style={{font=\fontsize{{{style.label_size}}}{{{style.label_size + 1}}}\selectfont}},",
            rf"    legend style={{draw=none, font=\fontsize{{{style.legend_size}}}{{{style.legend_size + 1}}}\selectfont}},",
            r"    legend cell align={left},",
            r"  }",
            r"}",
        ]
    )


def _pgfplots_latex_block(figure: PgfplotsFigure, *, input_prefix: str) -> str:
    input_path = f"{input_prefix}{figure.tex_path.name}"
    return "\n".join(
        [
            r"\begin{figure}[t]",
            r"  \centering",
            rf"  \input{{{input_path}}}",
            rf"  \caption{{{_latex_escape(figure.caption)}}}",
            rf"  \label{{{figure.label}}}",
            r"\end{figure}",
        ]
    )


def _pgfplots_height(size: PublicationSize) -> str:
    if size.name == "half_column":
        return r"0.276\columnwidth"
    return r"0.333\columnwidth"


def _pgfplots_time_axis(x: np.ndarray, figure_cfg: dict[str, Any]) -> tuple[np.ndarray, float]:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x, 0.0

    shifted = x - float(x[0])
    axis_max = float(shifted[-1])

    processing = figure_cfg.get("processing")
    if isinstance(processing, dict):
        crop_window = processing.get("crop")
        if isinstance(crop_window, (list, tuple)) and len(crop_window) == 2:
            axis_max = max(0.0, float(crop_window[1]) - float(crop_window[0]))

    return shifted, axis_max


def _pgfplots_integer_final_tick(x_axis_max: float) -> int | None:
    rounded = round(x_axis_max)
    if rounded <= 0:
        return None
    if abs(x_axis_max - rounded) > 1e-9:
        return None
    return int(rounded)


def _pgfplots_best_legend_pos(x: np.ndarray, signal: np.ndarray) -> str:
    x = np.asarray(x)
    values = np.asarray(signal).reshape(signal.shape[0], -1)
    if x.size == 0 or values.size == 0:
        return "north east"

    y_min = float(np.nanmin(values))
    y_max = float(np.nanmax(values))
    if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min == y_max:
        return "north east"

    x_mid = float(x[0] + 0.65 * (x[-1] - x[0]))
    x_left_mid = float(x[0] + 0.35 * (x[-1] - x[0]))
    y_high = y_min + 0.65 * (y_max - y_min)
    y_low = y_min + 0.35 * (y_max - y_min)

    flattened_x = np.repeat(x, values.shape[1])
    flattened_y = values.reshape(-1)
    finite = np.isfinite(flattened_y)
    flattened_x = flattened_x[finite]
    flattened_y = flattened_y[finite]

    scores = {
        "north east": int(np.count_nonzero((flattened_x >= x_mid) & (flattened_y >= y_high))),
        "north west": int(np.count_nonzero((flattened_x <= x_left_mid) & (flattened_y >= y_high))),
        "south east": int(np.count_nonzero((flattened_x >= x_mid) & (flattened_y <= y_low))),
        "south west": int(np.count_nonzero((flattened_x <= x_left_mid) & (flattened_y <= y_low))),
    }
    return min(scores, key=scores.get)


def _pgf_number(value: float) -> str:
    return f"{value:.12g}"


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _latex_label(value: str) -> str:
    if value.startswith("$") and value.endswith("$"):
        return value
    return _latex_escape(value)


def _capitalize_label(value: str) -> str:
    for index, char in enumerate(value):
        if char.isalpha():
            return f"{value[:index]}{char.upper()}{value[index + 1:]}"
    return value
