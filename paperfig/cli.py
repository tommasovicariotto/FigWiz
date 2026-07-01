from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config, resolve_path
from .mat_loader import as_array, load_mat_file, variable_summary
from .processing import apply_processing
from .plotly_viewer import make_timeseries_figure, save_or_show

app = typer.Typer(help="Config-driven .mat figure inspection tool.")
console = Console()


def _load_from_config(config_path: Path):
    cfg = load_config(config_path)
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

    data_cfg = cfg.get("data", {})
    time_name = data_cfg.get("time", "t")
    if time_name not in mat_data:
        raise typer.BadParameter(f"Time variable '{time_name}' not found in MAT file.")
    time = as_array(mat_data[time_name], time_name)

    signals_cfg = cfg.get("signals", {})
    figures = cfg.get("figures", [])
    if not figures:
        raise typer.BadParameter("Config contains no figures.")

    output_dir = resolve_path(config, cfg.get("output", {}).get("html_dir", "outputs/html"))

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
        time_p, signal_p = apply_processing(time, raw_signal, fig_cfg.get("processing"))
        plot_type = fig_cfg.get("plot", "timeseries")

        if plot_type != "timeseries":
            raise typer.BadParameter(f"Day 1 MVP only supports plot: timeseries. Got '{plot_type}'.")

        fig = make_timeseries_figure(time_p, signal_p, fig_cfg, sig_cfg)
        out_path = output_dir / f"{fig_name}.html"
        save_or_show(fig, out_path, open_browser=not no_browser)
        generated.append(out_path)
        console.print(f"[green]Generated[/green] {out_path}")

    if not generated:
        console.print("[yellow]No figures generated.[/yellow]")
