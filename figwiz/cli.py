from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import ConfigError, load_config, resolve_output_path, resolve_path
from .mat_loader import as_array, load_mat_file, variable_summary
from .processing import apply_array_processing, apply_processing, sample_time_axis
from .plotly_viewer import make_array_figure, make_timeseries_figure, save_dashboard

app = typer.Typer(help="Configuration-driven MATLAB experiment figure tool.")
console = Console()
FIGURES_PER_HTML = 6


def _load_from_config(config_path: Path):
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    mat_path = resolve_path(config_path, cfg["data"]["file"])
    mat_data = load_mat_file(mat_path)
    return cfg, mat_path, mat_data


@app.command()
def inspect(config: Path = typer.Argument(..., help="Path to YAML config.")):
    """Inspect variables available in the configured .mat file."""
    cfg, mat_path, mat_data = _load_from_config(config)
    console.print(f"[bold]MAT file:[/bold] {mat_path}")

    table = Table(title="Available variables")
    table.add_column("Name", style="cyan")
    table.add_column("Shape")
    table.add_column("Dtype/type")

    for name, shape, dtype in variable_summary(mat_data):
        table.add_row(name, shape, dtype)
    console.print(table)

    signals = cfg.get("signals", {})
    if signals:
        map_table = Table(title="Configured signal mappings")
        map_table.add_column("Semantic name", style="green")
        map_table.add_column("Source variable")
        map_table.add_column("Status")
        for semantic_name, sig_cfg in signals.items():
            source = sig_cfg.get("source", semantic_name) if isinstance(sig_cfg, dict) else str(sig_cfg)
            status = "OK" if source in mat_data else "MISSING"
            map_table.add_row(semantic_name, source, status)
        console.print(map_table)


@app.command()
def view(
    config: Path = typer.Argument(..., help="Path to YAML config."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Save HTML but do not open browser."),
    only: Optional[str] = typer.Option(None, "--only", help="Only render one figure by name."),
):
    """Create interactive Plotly figures from the config."""
    cfg, mat_path, mat_data = _load_from_config(config)
    console.print(f"[bold]MAT file:[/bold] {mat_path}")

    signals_cfg = cfg.get("signals", {})
    figures = cfg.get("figures", [])
    if not figures:
        raise typer.BadParameter("Config contains no figures.")

    output_dir = resolve_output_path(config, cfg, cfg.get("output", {}).get("html_dir", "outputs/html"))
    sample_down = cfg.get("data", {}).get("sample_down")

    rendered_figures = []
    for fig_cfg in figures:
        fig_name = fig_cfg.get("name")
        if only and fig_name != only:
            continue

        semantic_signal = fig_cfg.get("signal")
        if semantic_signal not in signals_cfg:
            raise typer.BadParameter(f"Figure '{fig_name}' references unknown signal '{semantic_signal}'.")

        sig_cfg = signals_cfg[semantic_signal]
        source = sig_cfg.get("source", semantic_signal)
        if source not in mat_data:
            raise typer.BadParameter(f"Source variable '{source}' not found for signal '{semantic_signal}'.")

        raw_signal = as_array(mat_data[source], source)
        plot_type = fig_cfg.get("plot", "timeseries")

        if plot_type == "timeseries":
            data_cfg = cfg.get("data", {})
            time_name = data_cfg.get("time")
            if not time_name:
                raise typer.BadParameter(f"Figure '{fig_name}' uses plot: timeseries, but data.time is not configured.")
            if time_name not in mat_data:
                raise typer.BadParameter(f"Time variable '{time_name}' not found in MAT file.")
            time = as_array(mat_data[time_name], time_name)
            time_p, signal_p = apply_processing(time, raw_signal, fig_cfg.get("processing"), sample_down=sample_down)
            fig = make_timeseries_figure(time_p, signal_p, fig_cfg, sig_cfg)
        elif plot_type == "array":
            fs = float(cfg["data"]["fs"])
            signal_p, effective_fs, time_offset = apply_array_processing(
                raw_signal,
                fig_cfg.get("processing"),
                fs=fs,
                sample_down=sample_down,
            )
            fig = make_array_figure(signal_p, fig_cfg, sig_cfg, fs=effective_fs, time_offset=time_offset)
        else:
            raise typer.BadParameter(f"Unsupported plot type '{plot_type}'.")

        rendered_figures.append((fig_name, fig))

    if not rendered_figures:
        console.print("[yellow]No figures generated.[/yellow]")
        return

    generated = []
    stem = Path(config).stem
    for index in range(0, len(rendered_figures), FIGURES_PER_HTML):
        batch = rendered_figures[index : index + FIGURES_PER_HTML]
        batch_number = index // FIGURES_PER_HTML + 1
        suffix = "" if len(rendered_figures) <= FIGURES_PER_HTML else f"_{batch_number}"
        out_path = output_dir / f"{stem}{suffix}.html"
        save_dashboard(batch, out_path, open_browser=not no_browser)
        generated.append(out_path)
        console.print(f"[green]Generated[/green] {out_path}")


@app.command()
def generate(
    config: Path = typer.Argument(..., help="Path to YAML config."),
    only: Optional[str] = typer.Option(None, "--only", help="Only export one figure by name."),
):
    """Generate publication EPS figures and one psfrag LaTeX snippet."""
    try:
        from .publication import save_publication_figure, write_latex_snippet
    except ImportError as exc:
        raise typer.BadParameter("Publication export requires matplotlib. Install project dependencies first.") from exc

    cfg, mat_path, mat_data = _load_from_config(config)
    console.print(f"[bold]MAT file:[/bold] {mat_path}")

    signals_cfg = cfg.get("signals", {})
    figures = cfg.get("figures", [])
    if not figures:
        raise typer.BadParameter("Config contains no figures.")

    output_cfg = cfg.get("output", {})
    eps_dir = resolve_output_path(config, cfg, output_cfg.get("eps_dir", "outputs/paper/eps"))
    latex_path = resolve_output_path(config, cfg, output_cfg.get("latex_file", "outputs/paper/figures.tex"))
    sample_down = cfg.get("data", {}).get("sample_down")

    exported = []
    for fig_cfg in figures:
        fig_name = fig_cfg.get("name")
        if only and fig_name != only:
            continue

        semantic_signal = fig_cfg.get("signal")
        if semantic_signal not in signals_cfg:
            raise typer.BadParameter(f"Figure '{fig_name}' references unknown signal '{semantic_signal}'.")

        sig_cfg = signals_cfg[semantic_signal]
        source = sig_cfg.get("source", semantic_signal)
        if source not in mat_data:
            raise typer.BadParameter(f"Source variable '{source}' not found for signal '{semantic_signal}'.")

        raw_signal = as_array(mat_data[source], source)
        plot_type = fig_cfg.get("plot", "timeseries")

        if plot_type == "timeseries":
            data_cfg = cfg.get("data", {})
            time_name = data_cfg.get("time")
            if not time_name:
                raise typer.BadParameter(f"Figure '{fig_name}' uses plot: timeseries, but data.time is not configured.")
            if time_name not in mat_data:
                raise typer.BadParameter(f"Time variable '{time_name}' not found in MAT file.")
            time = as_array(mat_data[time_name], time_name)
            x, signal = apply_processing(time, raw_signal, fig_cfg.get("processing"), sample_down=sample_down)
        elif plot_type == "array":
            fs = float(cfg["data"]["fs"])
            signal, effective_fs, time_offset = apply_array_processing(
                raw_signal,
                fig_cfg.get("processing"),
                fs=fs,
                sample_down=sample_down,
            )
            x = sample_time_axis(signal.shape[0], effective_fs) + time_offset
        else:
            raise typer.BadParameter(f"Unsupported plot type '{plot_type}'.")

        exported_figure = save_publication_figure(x, signal, fig_cfg, sig_cfg, eps_dir)
        exported.append(exported_figure)
        console.print(f"[green]Generated[/green] {exported_figure.eps_path}")

    if not exported:
        console.print("[yellow]No figures generated.[/yellow]")
        return

    write_latex_snippet(exported, latex_path, graphics_prefix="")
    console.print(f"[green]Generated[/green] {latex_path}")


@app.command()
def report(
    config: Path = typer.Argument(..., help="Path to YAML config."),
    only: Optional[str] = typer.Option(None, "--only", help="Only export one figure by name."),
):
    """Generate report-ready PDF figures with real labels."""
    try:
        from .publication import save_report_figure
    except ImportError as exc:
        raise typer.BadParameter("Report export requires matplotlib. Install project dependencies first.") from exc

    cfg, mat_path, mat_data = _load_from_config(config)
    console.print(f"[bold]MAT file:[/bold] {mat_path}")

    signals_cfg = cfg.get("signals", {})
    figures = cfg.get("figures", [])
    if not figures:
        raise typer.BadParameter("Config contains no figures.")

    output_cfg = cfg.get("output", {})
    report_dir = resolve_output_path(config, cfg, output_cfg.get("report_dir", "outputs/report"))
    sample_down = cfg.get("data", {}).get("sample_down")

    generated = []
    for fig_cfg in figures:
        fig_name = fig_cfg.get("name")
        if only and fig_name != only:
            continue

        semantic_signal = fig_cfg.get("signal")
        if semantic_signal not in signals_cfg:
            raise typer.BadParameter(f"Figure '{fig_name}' references unknown signal '{semantic_signal}'.")

        sig_cfg = signals_cfg[semantic_signal]
        source = sig_cfg.get("source", semantic_signal)
        if source not in mat_data:
            raise typer.BadParameter(f"Source variable '{source}' not found for signal '{semantic_signal}'.")

        raw_signal = as_array(mat_data[source], source)
        plot_type = fig_cfg.get("plot", "timeseries")

        if plot_type == "timeseries":
            data_cfg = cfg.get("data", {})
            time_name = data_cfg.get("time")
            if not time_name:
                raise typer.BadParameter(f"Figure '{fig_name}' uses plot: timeseries, but data.time is not configured.")
            if time_name not in mat_data:
                raise typer.BadParameter(f"Time variable '{time_name}' not found in MAT file.")
            time = as_array(mat_data[time_name], time_name)
            x, signal = apply_processing(time, raw_signal, fig_cfg.get("processing"), sample_down=sample_down)
        elif plot_type == "array":
            fs = float(cfg["data"]["fs"])
            signal, effective_fs, time_offset = apply_array_processing(
                raw_signal,
                fig_cfg.get("processing"),
                fs=fs,
                sample_down=sample_down,
            )
            x = sample_time_axis(signal.shape[0], effective_fs) + time_offset
        else:
            raise typer.BadParameter(f"Unsupported plot type '{plot_type}'.")

        out_path = save_report_figure(x, signal, fig_cfg, sig_cfg, report_dir)
        generated.append(out_path)
        console.print(f"[green]Generated[/green] {out_path}")

    if not generated:
        console.print("[yellow]No figures generated.[/yellow]")
