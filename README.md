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
outputs/html/nominal/robotics_example.html
outputs/paper/eps/nominal/*.eps
outputs/paper/nominal/figures.txt
outputs/report/nominal/*.pdf
```

## Commands

Inspect variables and configured signals:

```bash
figwiz inspect configs/robotics_example.yaml
```

Create an interactive Plotly dashboard:

```bash
figwiz view configs/robotics_example.yaml
```

Create paper figures:

```bash
figwiz generate configs/robotics_example.yaml
```

This writes EPS files and one shared psfrag/include text file.

Create report figures:

```bash
figwiz report configs/robotics_example.yaml
```

This writes PDF files with real labels and legends, without LaTeX snippets.

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

## Config Model

A config describes the dataset, output identity, and figures:

```yaml
variables:
  experiment_name: nominal

run_id: "${experiment_name}"

data:
  file: "data/${experiment_name}.mat"
  time: t
  sample_down: 100

figures:
  - template: tcp_position_error
    signal: TCP_pos_err
    processing:
      crop: [7, 50]
      scale: 100
    y_label: position error [cm]
```

Key ideas:

- `run_id` keeps outputs from different datasets separate.
- `template` chooses reusable figure structure.
- `signal` points to the MATLAB variable or a configured signal alias.
- `processing` applies operations such as crop, scale, norm, and sample-down.
- `paper_size` controls EPS paper sizing: `column` or `half_column`.
- `legend` can be `false`, `true`, or a small mapping with `columns` and `location`.

## Outputs

Interactive dashboard:

```text
outputs/html/<run_id>/
```

Paper output:

```text
outputs/paper/eps/<run_id>/
outputs/paper/<run_id>/figures.txt
```

Report output:

```text
outputs/report/<run_id>/
```

## Tests

```bash
python -m unittest discover
python -m compileall -q figwiz tests
```

## License

MIT
