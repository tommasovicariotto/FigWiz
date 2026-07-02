# Development

## Local Setup

```bash
conda create -n figwiz312 python=3.12
conda activate figwiz312
pip install -e .
```

## Checks

```bash
python -m unittest discover
python -m compileall -q figwiz tests
```

## Where To Change Things

Use this guide before adding code:

```text
configs/                  change what to plot
figwiz/templates/          add reusable figure structures
figwiz/styles.py           change paper/report visual style
figwiz/processing.py       add signal operations
figwiz/publication.py      change EPS/PDF export behavior
figwiz/plotly_viewer.py    change HTML dashboard behavior
figwiz/config.py           change config schema/validation
figwiz/cli.py              add or wire commands
```

Prefer adding a config option before hardcoding behavior. Keep templates reusable and keep experiment-specific choices in YAML configs.
