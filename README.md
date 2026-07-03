# FigWiz

FigWiz is a Python CLI for turning MATLAB robotics experiment data into reusable figures.

It is built around one idea: **edit YAML configs, not plotting code**. The same config can inspect a `.mat` file, open an interactive dashboard, generate EPS figures for papers, and generate PDF figures for reports.

## Requirements

- Python 3.12+
- MATLAB `.mat` files containing numeric time-series or sampled array data

## Installation

```bash
git clone https://github.com/tommasovicariotto/figwiz.git
cd figwiz

python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Check the install:

```bash
figwiz --help
```

## Reproducible Example

The main example is:

```text
configs/robotics_example.yaml
```

Run the full workflow:

```bash
figwiz inspect configs/robotics_example.yaml
figwiz view configs/robotics_example.yaml --no-browser
figwiz generate configs/robotics_example.yaml
figwiz report configs/robotics_example.yaml
```

Expected outputs:

```text
outputs/nominal/html/robotics_example.html
outputs/nominal/paper/option_eps/eps/*.eps
outputs/nominal/paper/option_eps/figures.tex
outputs/nominal/paper/option_tikz/dat/*.dat
outputs/nominal/paper/option_tikz/pgfplots/*.tex
outputs/nominal/paper/option_tikz/figures_pgfplots.tex
outputs/nominal/report/*.pdf
```

## Architecture

FigWiz separates the project into small parts:

```text
configs/                    user-editable plotting recipes
  robotics_example.yaml      reproducible robotics example

figwiz/                     Python package
  templates/                reusable figure structures
    *.yaml                  built-in template definitions
  cli.py                    command-line entry points
  config.py                 strict config loading and validation
  processing.py             crop, scale, norm, sample down
  plotly_viewer.py          interactive HTML dashboard backend
  publication.py            Matplotlib EPS/PDF export backend
  styles.py                 reusable paper/report style definitions
```

For most use cases, modify only:

```text
configs/robotics_example.yaml
```

Create or edit templates only when you want a new reusable figure type:

```text
figwiz/templates/*.yaml
```

Edit Python modules only when adding new behavior, new processing operations, or new output backends.

## Commands

Inspect variables and configured signals:

```bash
figwiz inspect configs/robotics_example.yaml
```

Create an interactive Plotly dashboard:

```bash
figwiz view configs/robotics_example.yaml
```

Save the dashboard without opening a browser:

```bash
figwiz view configs/robotics_example.yaml --no-browser
```

Render one configured figure:

```bash
figwiz view configs/robotics_example.yaml --only tcp_position_error
```

Generate publication EPS figures, psfrag snippets, and PGFPlots/TikZ files:

```bash
figwiz generate configs/robotics_example.yaml
```

Generate report-ready PDF figures:

```bash
figwiz report configs/robotics_example.yaml
```

## Configuration

FigWiz is configured with YAML files. A config chooses the `.mat` file, maps semantic signal names to MATLAB variables, selects reusable figure templates, and sets output locations.

The main example config is:

```text
configs/robotics_example.yaml
```

More configuration notes are in:

```text
docs/config.md
```

## Development

Run checks with:

```bash
python -m unittest discover
python -m compileall -q figwiz tests
```

Development notes are in:

```text
docs/development.md
```
