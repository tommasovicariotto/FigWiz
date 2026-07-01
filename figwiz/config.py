from __future__ import annotations

import ast
import copy
import difflib
import operator
import re
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a configuration file is invalid."""


BUILTIN_STYLES: dict[str, dict[str, Any]] = {
    "ieee": {
        "legend": True,
        "x_label": "time [s]",
    },
}

TEMPLATE_DIR = Path(__file__).parent / "templates"

FIGURE_DEFAULTS: dict[str, Any] = {
    "plot": "timeseries",
    "x_label": "time [s]",
}

ALLOWED_PLOT_TYPES = {"array", "timeseries"}
TOP_LEVEL_FIELDS = {
    "data",
    "datasets",
    "extends",
    "figures",
    "output",
    "pipelines",
    "signals",
    "style",
    "styles",
    "template",
    "templates",
    "variables",
}
DATA_FIELDS = {"dataset", "file", "fs", "time"}
OUTPUT_FIELDS = {"html_dir"}
SIGNAL_FIELDS = {"components", "kind", "source", "unit"}
FIGURE_FIELDS = {
    "events",
    "legend",
    "name",
    "pipeline",
    "plot",
    "processing",
    "signal",
    "style",
    "template",
    "title",
    "x_label",
    "y_label",
}
PROCESSING_FIELDS = {"crop", "norm", "pipeline", "scale"}
EVENT_FIELDS = {"label", "time"}
MATH_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    raw_cfg = _load_raw_config(path, seen=set())
    substituted = _substitute_variables(raw_cfg)
    cfg = _expand_reusable_components(substituted)
    _expand_dataset_alias(cfg)
    _expand_pipeline_aliases(cfg)
    _validate_config(cfg)
    return cfg


def resolve_path(config_path: str | Path, possibly_relative_path: str | Path) -> Path:
    p = Path(possibly_relative_path)
    if p.is_absolute():
        return p
    return Path(config_path).parent.parent / p


def _load_raw_config(path: Path, seen: set[Path]) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if path in seen:
        raise ConfigError(f"Config extends cycle detected at: {path}")
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if not isinstance(cfg, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")

    _validate_unknown_fields(cfg, TOP_LEVEL_FIELDS, "top-level")

    extends = cfg.get("extends")
    if extends is None:
        return cfg
    if not isinstance(extends, str):
        raise ConfigError("'extends' must be a path string.")

    parent_path = Path(extends)
    if not parent_path.is_absolute():
        parent_path = path.parent / parent_path

    base_cfg = _load_raw_config(parent_path, seen | {path})
    user_cfg = dict(cfg)
    user_cfg.pop("extends", None)
    return _deep_merge(base_cfg, user_cfg)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _substitute_variables(cfg: dict[str, Any]) -> dict[str, Any]:
    variables = cfg.get("variables", {})
    if variables is None:
        variables = {}
    if not isinstance(variables, dict):
        raise ConfigError("'variables' must be a mapping.")

    return _substitute_value(cfg, variables)


def _substitute_value(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _substitute_value(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute_value(item, variables) for item in value]
    if not isinstance(value, str):
        return value

    if VARIABLE_PATTERN.search(value) is None:
        return value

    full_match = VARIABLE_PATTERN.fullmatch(value)
    if full_match:
        name = full_match.group(1)
        if name not in variables:
            raise ConfigError(f"Unknown variable '{name}' in config value.")
        return variables[name]

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise ConfigError(f"Unknown variable '{name}' in config value.")
        return str(variables[name])

    substituted = VARIABLE_PATTERN.sub(replace, value)
    numeric = _try_parse_number_expression(substituted)
    return numeric if numeric is not None else substituted


def _try_parse_number_expression(value: str) -> int | float | None:
    if not re.fullmatch(r"[0-9eE+\-*/().\s]+", value):
        return None
    try:
        tree = ast.parse(value, mode="eval")
        result = _eval_math_node(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError):
        return None
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result


def _eval_math_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and _is_number(node.value):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in MATH_OPERATORS:
            raise ValueError("Unsupported operator.")
        return MATH_OPERATORS[op_type](_eval_math_node(node.left), _eval_math_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in MATH_OPERATORS:
            raise ValueError("Unsupported unary operator.")
        return MATH_OPERATORS[op_type](_eval_math_node(node.operand))
    raise ValueError("Unsupported expression.")


def _expand_reusable_components(cfg: dict[str, Any]) -> dict[str, Any]:
    expanded = copy.deepcopy(cfg)
    styles = _component_map(expanded, "styles", BUILTIN_STYLES)
    templates = _component_map(expanded, "templates", _load_builtin_templates())

    top_style = expanded.get("style")
    top_template = expanded.get("template")
    if top_style is not None:
        _require_component(styles, top_style, "style")
    if top_template is not None:
        _require_component(templates, top_template, "template")

    figures = expanded.get("figures", [])
    if figures is None:
        figures = []
    if not isinstance(figures, list):
        raise ConfigError("'figures' must be a list.")

    merged_figures = []
    for index, figure in enumerate(figures):
        if not isinstance(figure, dict):
            raise ConfigError(f"'figures[{index}]' must be a mapping.")
        _validate_unknown_fields(figure, FIGURE_FIELDS, f"figures[{index}]")

        merged: dict[str, Any] = copy.deepcopy(FIGURE_DEFAULTS)
        if top_style is not None:
            merged = _deep_merge(merged, styles[str(top_style)])
        if top_template is not None:
            merged = _deep_merge(merged, templates[str(top_template)])

        figure_style = figure.get("style")
        figure_template = figure.get("template")
        if figure_style is not None:
            _require_component(styles, figure_style, f"figures[{index}].style")
            merged = _deep_merge(merged, styles[str(figure_style)])
        if figure_template is not None:
            _require_component(templates, figure_template, f"figures[{index}].template")
            merged = _deep_merge(merged, templates[str(figure_template)])

        merged = _deep_merge(merged, figure)
        merged_figures.append(merged)

    expanded["figures"] = merged_figures
    return expanded


def _component_map(cfg: dict[str, Any], field: str, builtins: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    custom = cfg.get(field, {})
    if custom is None:
        custom = {}
    if not isinstance(custom, dict):
        raise ConfigError(f"'{field}' must be a mapping.")

    components = copy.deepcopy(builtins)
    for name, value in custom.items():
        if not isinstance(name, str):
            raise ConfigError(f"'{field}' names must be strings.")
        if not isinstance(value, dict):
            raise ConfigError(f"'{field}.{name}' must be a mapping.")
        _validate_unknown_fields(value, FIGURE_FIELDS, f"{field}.{name}")
        components[name] = copy.deepcopy(value)
    return components


def _load_builtin_templates() -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    for template_file in sorted(TEMPLATE_DIR.iterdir()):
        if template_file.suffix not in {".yaml", ".yml"}:
            continue
        with template_file.open("r", encoding="utf-8") as f:
            template = yaml.safe_load(f) or {}
        if not isinstance(template, dict):
            raise ConfigError(f"Built-in template '{template_file.name}' must be a mapping.")
        _validate_unknown_fields(template, FIGURE_FIELDS, f"template {template_file.stem}")
        templates[template_file.stem] = template
    return templates


def _require_component(components: dict[str, dict[str, Any]], name: Any, location: str) -> None:
    if not isinstance(name, str):
        raise ConfigError(f"'{location}' must be a string.")
    if name not in components:
        raise ConfigError(_unknown_name_message(location, name, components.keys()))


def _expand_dataset_alias(cfg: dict[str, Any]) -> None:
    datasets = cfg.get("datasets", {})
    if datasets is None:
        datasets = {}
    if not isinstance(datasets, dict):
        raise ConfigError("'datasets' must be a mapping.")
    for name, dataset in datasets.items():
        if not isinstance(dataset, dict):
            raise ConfigError(f"'datasets.{name}' must be a mapping.")
        _validate_unknown_fields(dataset, DATA_FIELDS - {"dataset"}, f"datasets.{name}")
        _require_string(dataset, "file", f"datasets.{name}")
        _optional_string(dataset, "time", f"datasets.{name}")

    data = cfg.get("data")
    if data is None:
        return
    if not isinstance(data, dict):
        raise ConfigError("'data' must be a mapping.")
    _validate_unknown_fields(data, DATA_FIELDS, "data")

    dataset_name = data.get("dataset")
    if dataset_name is None:
        return
    if not isinstance(dataset_name, str):
        raise ConfigError("'data.dataset' must be a string.")
    if dataset_name not in datasets:
        raise ConfigError(_unknown_name_message("data.dataset", dataset_name, datasets.keys()))

    overrides = dict(data)
    overrides.pop("dataset", None)
    cfg["data"] = _deep_merge(datasets[dataset_name], overrides)


def _expand_pipeline_aliases(cfg: dict[str, Any]) -> None:
    pipelines = cfg.get("pipelines", {})
    if pipelines is None:
        pipelines = {}
    if not isinstance(pipelines, dict):
        raise ConfigError("'pipelines' must be a mapping.")

    for name, pipeline in pipelines.items():
        if not isinstance(pipeline, dict):
            raise ConfigError(f"'pipelines.{name}' must be a mapping.")
        _validate_processing(pipeline, f"pipelines.{name}", allow_pipeline_reference=False)

    for index, figure in enumerate(cfg.get("figures", [])):
        pipeline_name = figure.get("pipeline")
        processing = figure.get("processing")
        if isinstance(processing, dict) and processing.get("pipeline") is not None:
            if pipeline_name is not None:
                raise ConfigError(f"'figures[{index}]' cannot define both 'pipeline' and 'processing.pipeline'.")
            pipeline_name = processing.get("pipeline")
            processing = {key: value for key, value in processing.items() if key != "pipeline"}

        if pipeline_name is None:
            figure["processing"] = processing or {}
            continue
        if not isinstance(pipeline_name, str):
            raise ConfigError(f"'figures[{index}].pipeline' must be a string.")
        if pipeline_name not in pipelines:
            raise ConfigError(_unknown_name_message(f"figures[{index}].pipeline", pipeline_name, pipelines.keys()))

        if processing is None:
            processing = {}
        if not isinstance(processing, dict):
            raise ConfigError(f"'figures[{index}].processing' must be a mapping.")
        figure["processing"] = _deep_merge(pipelines[pipeline_name], processing)


def _validate_config(cfg: dict[str, Any]) -> None:
    _validate_unknown_fields(cfg, TOP_LEVEL_FIELDS, "top-level")

    data = cfg.get("data")
    if data is None:
        raise ConfigError("Missing required field 'data'.")
    if not isinstance(data, dict):
        raise ConfigError("'data' must be a mapping.")
    _validate_unknown_fields(data, DATA_FIELDS - {"dataset"}, "data")
    _require_string(data, "file", "data")
    if "fs" not in data:
        data["fs"] = 1000
    if not _is_number(data["fs"]) or data["fs"] <= 0:
        raise ConfigError("'data.fs' must be a positive number.")
    _optional_string(data, "time", "data")

    output = cfg.get("output", {})
    if output is not None:
        if not isinstance(output, dict):
            raise ConfigError("'output' must be a mapping.")
        _validate_unknown_fields(output, OUTPUT_FIELDS, "output")
        _optional_string(output, "html_dir", "output")

    _validate_signals(cfg.get("signals"))
    _validate_figures(cfg.get("figures"), cfg["signals"], data)


def _validate_signals(signals: Any) -> None:
    if signals is None:
        raise ConfigError("Missing required field 'signals'.")
    if not isinstance(signals, dict):
        raise ConfigError("'signals' must be a mapping.")
    if not signals:
        raise ConfigError("'signals' must contain at least one signal.")

    for name, signal in signals.items():
        if not isinstance(name, str):
            raise ConfigError("'signals' names must be strings.")
        if not isinstance(signal, dict):
            raise ConfigError(f"'signals.{name}' must be a mapping.")
        _validate_unknown_fields(signal, SIGNAL_FIELDS, f"signals.{name}")
        _require_string(signal, "source", f"signals.{name}")
        _optional_string(signal, "kind", f"signals.{name}")
        _optional_string(signal, "unit", f"signals.{name}")
        components = signal.get("components")
        if components is not None:
            if not isinstance(components, list) or not all(isinstance(item, str) for item in components):
                raise ConfigError(f"'signals.{name}.components' must be a list of strings.")


def _validate_figures(figures: Any, signals: dict[str, Any], data: dict[str, Any]) -> None:
    if figures is None:
        raise ConfigError("Missing required field 'figures'.")
    if not isinstance(figures, list):
        raise ConfigError("'figures' must be a list.")
    if not figures:
        raise ConfigError("'figures' must contain at least one figure.")

    for index, figure in enumerate(figures):
        location = f"figures[{index}]"
        if not isinstance(figure, dict):
            raise ConfigError(f"'{location}' must be a mapping.")
        _validate_unknown_fields(figure, FIGURE_FIELDS, location)
        _require_string(figure, "name", location)
        _require_string(figure, "signal", location)
        if figure["signal"] not in signals:
            raise ConfigError(_unknown_name_message(f"{location}.signal", figure["signal"], signals.keys()))

        plot = figure.get("plot")
        if not isinstance(plot, str):
            raise ConfigError(f"'{location}.plot' must be a string.")
        if plot not in ALLOWED_PLOT_TYPES:
            raise ConfigError(_unknown_name_message(f"{location}.plot", plot, ALLOWED_PLOT_TYPES))
        if plot == "timeseries" and "time" not in data:
            raise ConfigError(f"'{location}' uses plot: timeseries, so 'data.time' is required.")

        _optional_string(figure, "title", location)
        _optional_string(figure, "x_label", location)
        _optional_string(figure, "y_label", location)
        if "legend" in figure and not isinstance(figure["legend"], bool):
            raise ConfigError(f"'{location}.legend' must be a boolean.")
        _validate_processing(figure.get("processing", {}), f"{location}.processing", allow_pipeline_reference=False)
        _validate_events(figure.get("events", []), location)


def _validate_processing(processing: Any, location: str, *, allow_pipeline_reference: bool) -> None:
    if processing is None:
        return
    if not isinstance(processing, dict):
        raise ConfigError(f"'{location}' must be a mapping.")
    allowed = PROCESSING_FIELDS if allow_pipeline_reference else PROCESSING_FIELDS - {"pipeline"}
    _validate_unknown_fields(processing, allowed, location)
    crop_value = processing.get("crop")
    if crop_value is not None:
        if not isinstance(crop_value, (list, tuple)) or len(crop_value) != 2:
            raise ConfigError(f"'{location}.crop' must be a two-item list.")
        for item in crop_value:
            if not _is_number(item):
                raise ConfigError(f"'{location}.crop' values must be numbers.")
    if "scale" in processing and not _is_number(processing["scale"]):
        raise ConfigError(f"'{location}.scale' must be a number.")
    if "norm" in processing and not isinstance(processing["norm"], bool):
        raise ConfigError(f"'{location}.norm' must be a boolean.")


def _validate_events(events: Any, figure_location: str) -> None:
    if events is None:
        return
    if not isinstance(events, list):
        raise ConfigError(f"'{figure_location}.events' must be a list.")
    for index, event in enumerate(events):
        location = f"{figure_location}.events[{index}]"
        if not isinstance(event, dict):
            raise ConfigError(f"'{location}' must be a mapping.")
        _validate_unknown_fields(event, EVENT_FIELDS, location)
        if "time" not in event:
            raise ConfigError(f"Missing required field '{location}.time'.")
        if not _is_number(event["time"]):
            raise ConfigError(f"'{location}.time' must be a number.")
        _optional_string(event, "label", location)


def _require_string(data: dict[str, Any], field: str, location: str) -> None:
    if field not in data:
        raise ConfigError(f"Missing required field '{location}.{field}'.")
    if not isinstance(data[field], str):
        raise ConfigError(f"'{location}.{field}' must be a string.")


def _optional_string(data: dict[str, Any], field: str, location: str) -> None:
    if field in data and data[field] is not None and not isinstance(data[field], str):
        raise ConfigError(f"'{location}.{field}' must be a string.")


def _validate_unknown_fields(data: dict[str, Any], allowed: set[str], location: str) -> None:
    for field in data:
        if field not in allowed:
            message = f"Unknown field '{location}.{field}'."
            suggestion = _closest(field, allowed)
            if suggestion:
                message += f" Did you mean '{suggestion}'?"
            raise ConfigError(message)


def _unknown_name_message(location: str, name: str, choices: Any) -> str:
    choice_list = sorted(str(choice) for choice in choices)
    message = f"Unknown {location} '{name}'."
    suggestion = _closest(name, set(choice_list))
    if suggestion:
        message += f" Did you mean '{suggestion}'?"
    if choice_list:
        message += f" Available: {', '.join(choice_list)}."
    return message


def _closest(value: str, choices: set[str]) -> str | None:
    matches = difflib.get_close_matches(value, sorted(choices), n=1, cutoff=0.75)
    return matches[0] if matches else None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
