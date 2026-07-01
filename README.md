# FigWiz

FigWiz is a Python command-line tool for generating publication-quality figures from MATLAB experiment data.

It provides a reproducible, configuration-driven workflow for loading `.mat` files, processing signals, and producing interactive visualizations.

## Features

- Configuration-driven figure generation with YAML
- MATLAB `.mat` data loading
- Interactive Plotly dashboard
- Reusable plotting templates
- Signal processing pipeline with crop, scaling, and derived quantities
- Command-line interface

## Installation

```bash
git clone https://github.com/tommasovicariotto/figwiz.git
cd figwiz
pip install .
```

For local development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Inspect available signals:

```bash
figwiz inspect configs/basic.yaml
```

Open an interactive dashboard:

```bash
figwiz view configs/basic.yaml
```

Save interactive HTML without opening a browser:

```bash
figwiz view configs/basic.yaml --no-browser
```

## Configuration

The `.mat` file contains raw data. The YAML config tells FigWiz what the data means and how to plot it.

```yaml
figures:
  - name: tcp_position_error
    signal: tcp_pos_err
    plot: timeseries
    processing:
      crop: [7, 50]
      scale: 100
```

This loads the semantic signal `tcp_pos_err`, crops the time vector between 7 and 50 seconds, multiplies values by 100, and plots it as a time series.

## Philosophy

FigWiz separates experiment data, plotting configuration, and rendering logic. Figures are defined declaratively through configuration files, enabling reproducible figure generation across experiments and publications.

## License

MIT
