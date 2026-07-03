from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from figwiz.config import ConfigError, load_config, resolve_output_path
import numpy as np

from figwiz.processing import apply_array_processing, apply_processing, sample_time_axis


ROOT = Path(__file__).resolve().parents[1]


def write_config(data: dict[str, Any]) -> Path:
    path = Path(tempfile.mkdtemp()) / "config.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def minimal_config(**overrides: Any) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "data": {"file": "data/nominal.mat", "time": "t"},
        "signals": {
            "tcp_pos_err": {
                "source": "TCP_pos_err",
                "kind": "vector",
                "components": ["x", "y", "z"],
                "unit": "m",
            }
        },
        "figures": [
            {
                "name": "tcp_position_error",
                "signal": "tcp_pos_err",
                "plot": "timeseries",
            }
        ],
    }
    cfg.update(overrides)
    return cfg


class ConfigTests(unittest.TestCase):
    def test_robotics_example_yaml_loads(self) -> None:
        cfg = load_config(ROOT / "configs" / "robotics_example.yaml")

        self.assertEqual(cfg["run_id"], "nominal")
        self.assertEqual(len(cfg["figures"]), 4)
        self.assertEqual(cfg["figures"][0]["plot"], "timeseries")
        self.assertNotIn("crop", cfg["figures"][0]["processing"])

    def test_style_merge(self) -> None:
        path = write_config(minimal_config(style="ieee"))

        cfg = load_config(path)

        self.assertIs(cfg["figures"][0]["legend"], True)
        self.assertEqual(cfg["figures"][0]["x_label"], "time [s]")

    def test_template_merge(self) -> None:
        figure = {"name": "tcp_position_error", "signal": "tcp_pos_err"}
        path = write_config(minimal_config(template="line_time_series", figures=[figure]))

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["plot"], "timeseries")
        self.assertEqual(cfg["figures"][0]["x_label"], "time [s]")

    def test_builtin_templates_are_yaml_files(self) -> None:
        expected_templates = {
            "base_pos_des",
            "base_pos_msr",
            "base_rpy_des",
            "base_rpy_msr",
            "base_twist",
            "force_torque",
            "joint_states",
            "kinetic_energy",
            "line_array",
            "line_time_series",
            "momentum_components",
            "momentum_norm",
            "q_pos_msr",
            "q_tau_msr",
            "q_vel_msr",
            "tcp_pos_ipol",
            "tcp_position_error",
            "tcp_rotation_error",
            "tcp_rpy_ipol",
        }

        template_names = {path.stem for path in (ROOT / "figwiz" / "templates").glob("*.yaml")}

        self.assertTrue(expected_templates.issubset(template_names))

    def test_robotics_template_signal_shorthand(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "tcp_position_error",
                        "signal": "TCP_pos_err",
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["name"], "tcp_position_error")
        self.assertEqual(cfg["figures"][0]["title"], "TCP position error")
        self.assertEqual(cfg["figures"][0]["plot"], "timeseries")
        self.assertEqual(cfg["signals"]["TCP_pos_err"]["source"], "TCP_pos_err")
        self.assertEqual(cfg["signals"]["TCP_pos_err"]["components"], ["x", "y", "z"])

    def test_rotation_signal_shorthand_uses_latex_angle_labels(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "tcp_rotation_error",
                        "signal": "TCP_rot_err",
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["signals"]["TCP_rot_err"]["components"], [r"$\alpha$", r"$\beta$", r"$\gamma$"])

    def test_joint_position_signal_shorthand_does_not_use_xyz_labels(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "q_pos_msr",
                        "signal": "q_pos_msr",
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertNotIn("components", cfg["signals"]["q_pos_msr"])

    def test_template_processing_merges_with_user_processing(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "momentum_norm",
                        "signal": "momentum",
                        "processing": {"crop": [7, 50]},
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["processing"], {"norm": True, "crop": [7, 50]})

    def test_rpy_templates_convert_rad_to_deg(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {"template": "base_rpy_msr", "signal": "base_rpy_msr"},
                    {"template": "base_rpy_des", "signal": "base_rpy_des"},
                    {"template": "tcp_rpy_ipol", "signal": "tcp_rpy_ipol"},
                ],
            }
        )

        cfg = load_config(path)

        for figure in cfg["figures"]:
            self.assertIn("[deg]", figure["y_label"])
            self.assertEqual(figure["processing"], {"scale": 57.29577951308232})

    def test_desired_and_interpolated_template_labels(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {"template": "base_pos_des", "signal": "base_pos_des"},
                    {"template": "base_rpy_des", "signal": "base_rpy_des"},
                    {"template": "tcp_pos_ipol", "signal": "tcp_pos_ipol"},
                    {"template": "tcp_rpy_ipol", "signal": "tcp_rpy_ipol"},
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["y_label"], "base position des. [m]")
        self.assertEqual(cfg["figures"][1]["y_label"], "base RPY des. [deg]")
        self.assertEqual(cfg["figures"][2]["y_label"], "TCP position des. ipol [m]")
        self.assertEqual(cfg["figures"][3]["y_label"], "TCP RPY des. ipol [deg]")

    def test_array_template_does_not_require_time(self) -> None:
        path = write_config(
            minimal_config(
                data={"file": "data/nominal.mat"},
                template="line_array",
                figures=[{"name": "samples", "signal": "tcp_pos_err"}],
            )
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["plot"], "array")
        self.assertEqual(cfg["figures"][0]["x_label"], "time [s]")
        self.assertEqual(cfg["data"]["fs"], 1000)
        self.assertEqual(cfg["data"]["sample_down"], 100)

    def test_array_config_accepts_fs(self) -> None:
        path = write_config(
            minimal_config(
                data={"file": "data/nominal.mat", "fs": 500},
                template="line_array",
                figures=[{"name": "samples", "signal": "tcp_pos_err"}],
            )
        )

        cfg = load_config(path)

        self.assertEqual(cfg["data"]["fs"], 500)

    def test_sample_down_can_be_disabled(self) -> None:
        path = write_config(
            minimal_config(
                data={"file": "data/nominal.mat", "fs": 500, "sample_down": False},
                template="line_array",
                figures=[{"name": "samples", "signal": "tcp_pos_err"}],
            )
        )

        cfg = load_config(path)

        self.assertIs(cfg["data"]["sample_down"], False)

    def test_array_plot_uses_fs_for_x_axis(self) -> None:
        x = sample_time_axis(n_samples=3, fs=1000)

        self.assertEqual(list(x), [0.0, 0.001, 0.002])

    def test_timeseries_sample_down_default_targets_100_hz(self) -> None:
        time = np.arange(1000) / 1000
        signal = np.arange(1000)

        time_p, signal_p = apply_processing(time, signal, {}, sample_down=100)

        self.assertEqual(len(time_p), 100)
        self.assertEqual(list(time_p[:3]), [0.0, 0.01, 0.02])
        self.assertEqual(list(signal_p[:3]), [0, 10, 20])

    def test_array_sample_down_returns_effective_fs(self) -> None:
        signal = np.arange(1000)

        signal_p, effective_fs, time_offset = apply_array_processing(signal, {}, fs=1000, sample_down=100)

        self.assertEqual(len(signal_p), 100)
        self.assertEqual(effective_fs, 100)
        self.assertEqual(time_offset, 0.0)
        self.assertEqual(list(signal_p[:3]), [0, 10, 20])

    def test_array_crop_uses_seconds(self) -> None:
        signal = np.arange(1000)

        signal_p, effective_fs, time_offset = apply_array_processing(
            signal,
            {"crop": [0.1, 0.2]},
            fs=1000,
            sample_down=False,
        )

        self.assertEqual(effective_fs, 1000)
        self.assertEqual(time_offset, 0.1)
        self.assertEqual(list(signal_p[:3]), [100, 101, 102])
        self.assertEqual(signal_p[-1], 200)

    def test_timeseries_requires_time(self) -> None:
        path = write_config(minimal_config(data={"file": "data/nominal.mat"}))

        with self.assertRaisesRegex(ConfigError, "data.time"):
            load_config(path)

    def test_variable_substitution(self) -> None:
        path = write_config(
            minimal_config(
                variables={"fs": 100, "experiment_name": "nominal"},
                data={"file": "data/${experiment_name}.mat", "time": "t"},
                figures=[
                    {
                        "name": "tcp_position_error",
                        "signal": "tcp_pos_err",
                        "processing": {"scale": "1/${fs}"},
                    }
                ],
            )
        )

        cfg = load_config(path)

        self.assertEqual(cfg["data"]["file"], "data/nominal.mat")
        self.assertEqual(cfg["figures"][0]["processing"]["scale"], 0.01)

    def test_run_id_variable_substitution(self) -> None:
        path = write_config(
            minimal_config(
                variables={"experiment_name": "nominal"},
                run_id="${experiment_name}",
            )
        )

        cfg = load_config(path)

        self.assertEqual(cfg["run_id"], "nominal")

    def test_run_id_namespaces_output_directories_and_files(self) -> None:
        path = write_config(minimal_config(run_id="nominal"))
        cfg = load_config(path)

        html_dir = resolve_output_path(path, cfg, "outputs/html")
        latex_file = resolve_output_path(path, cfg, "outputs/paper/option_eps/figures.tex")

        self.assertEqual(html_dir, path.parent.parent / "outputs" / "nominal" / "html")
        self.assertEqual(
            latex_file,
            path.parent.parent / "outputs" / "nominal" / "paper" / "option_eps" / "figures.tex",
        )

    def test_invalid_run_id(self) -> None:
        path = write_config(minimal_config(run_id="../bad"))

        with self.assertRaisesRegex(ConfigError, "run_id"):
            load_config(path)

    def test_legend_false_is_valid(self) -> None:
        path = write_config(
            minimal_config(
                figures=[
                    {
                        "name": "tcp_position_error",
                        "signal": "tcp_pos_err",
                        "plot": "timeseries",
                        "legend": False,
                    }
                ]
            )
        )

        cfg = load_config(path)

        self.assertIs(cfg["figures"][0]["legend"], False)

    def test_legend_columns_are_valid(self) -> None:
        path = write_config(
            minimal_config(
                figures=[
                    {
                        "name": "tcp_position_error",
                        "signal": "tcp_pos_err",
                        "plot": "timeseries",
                        "legend": {"columns": 3, "location": "upper right"},
                    }
                ]
            )
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["legend"]["columns"], 3)

    def test_invalid_legend_columns(self) -> None:
        path = write_config(
            minimal_config(
                figures=[
                    {
                        "name": "tcp_position_error",
                        "signal": "tcp_pos_err",
                        "plot": "timeseries",
                        "legend": {"columns": 0},
                    }
                ]
            )
        )

        with self.assertRaisesRegex(ConfigError, "legend.columns"):
            load_config(path)

    def test_dataset_alias_validation(self) -> None:
        path = write_config(minimal_config(data={"dataset": "missing"}, datasets={}))

        with self.assertRaisesRegex(ConfigError, "Unknown data.dataset 'missing'"):
            load_config(path)

    def test_pipeline_validation(self) -> None:
        path = write_config(minimal_config(figures=[{"name": "bad", "signal": "tcp_pos_err", "pipeline": "missing"}]))

        with self.assertRaisesRegex(ConfigError, "Unknown figures\\[0\\].pipeline 'missing'"):
            load_config(path)

    def test_builtin_rad_to_deg_pipeline(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "tcp_rotation_error",
                        "signal": "TCP_rot_err",
                        "pipeline": "rad_to_deg",
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["y_label"], "rotation error [deg]")
        self.assertAlmostEqual(cfg["figures"][0]["processing"]["scale"], 57.29577951308232)

    def test_builtin_deg_to_rad_pipeline(self) -> None:
        path = write_config(
            {
                "data": {"file": "data/nominal.mat", "time": "t"},
                "figures": [
                    {
                        "template": "tcp_rotation_error",
                        "signal": "TCP_rot_err",
                        "pipeline": "deg_to_rad",
                        "y_label": "rotation error [rad]",
                    }
                ],
            }
        )

        cfg = load_config(path)

        self.assertEqual(cfg["figures"][0]["y_label"], "rotation error [rad]")
        self.assertAlmostEqual(cfg["figures"][0]["processing"]["scale"], 0.017453292519943295)

    def test_unknown_field_typo_suggestion(self) -> None:
        path = write_config(
            minimal_config(
                figures=[
                    {
                        "name": "tcp_position_error",
                        "signal": "tcp_pos_err",
                        "plot": "timeseries",
                        "legnd": True,
                    }
                ]
            )
        )

        with self.assertRaisesRegex(ConfigError, "Did you mean 'legend'"):
            load_config(path)

    def test_missing_required_field(self) -> None:
        cfg = minimal_config()
        cfg.pop("data")
        path = write_config(cfg)

        with self.assertRaisesRegex(ConfigError, "Missing required field 'data'"):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
