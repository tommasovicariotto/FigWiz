# Configuration

FigWiz configs are YAML files. The config is the main user interface: it tells FigWiz which data to load, which variables to plot, which templates to use, and where outputs should go.

## Main Sections

```yaml
variables:    # optional values reused with ${...}
run_id:       # optional output namespace
data:         # required dataset information
output:       # optional output folders/files
figures:      # required figure list
pipelines:    # optional reusable processing blocks
signals:      # optional aliases for MATLAB variables
```

Most new experiments should start by copying an existing config and changing:

- `variables.experiment_name`
- `run_id`
- `data.file`
- `figures`
- labels and processing windows

## Dataset

```yaml
data:
  file: data/nominal.mat
  time: t
  fs: 1000
  sample_down: 100
```

For time-series plots, `time` is required. For array plots, `fs` is used to build the time axis.

`sample_down: 100` is the default. It keeps outputs lighter by plotting at about 100 Hz when the source data is faster. Disable it with:

```yaml
data:
  sample_down: false
```

## Outputs

```yaml
run_id: nominal

output:
  eps_dir: outputs/paper/eps
  latex_file: outputs/paper/figures.txt
  report_dir: outputs/report
```

With `run_id: nominal`, outputs are written under `nominal` subfolders.

## Figures

```yaml
figures:
  - template: tcp_position_error
    signal: TCP_pos_err
    paper_size: column
    processing:
      crop: [7, 50]
      scale: 100
    y_label: position error [cm]
```

Templates define the structure of a common figure. The config defines the dataset-specific choices: signal, units, crop window, scaling, legend, and output size.

## Legends

```yaml
legend: false
```

or:

```yaml
legend:
  columns: 3
  location: best
```

`location: best` uses Matplotlib's automatic legend placement for paper/report output.

## Pipelines

Pipelines are reusable processing blocks:

```yaml
pipelines:
  paper_window:
    crop: [7, 50]
```

Built-in pipelines include:

```yaml
pipeline: rad_to_deg
pipeline: deg_to_rad
```

## Templates

Built-in templates live in:

```text
figwiz/templates/
```

Add a new template when a figure structure is reused across multiple configs. Keep experiment-specific details in the config.
