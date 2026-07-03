from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from figwiz.cli import _resolve_run_scoped_subdir


class CliTests(unittest.TestCase):
    def test_run_scoped_subdir_places_leaf_inside_run_folder(self) -> None:
        config_path = Path(tempfile.mkdtemp()) / "configs" / "example.yaml"
        cfg = {"run_id": "nominal"}

        path = _resolve_run_scoped_subdir(
            config_path,
            cfg,
            "outputs/paper/option_eps/eps",
            default_name="eps",
            parent=config_path.parent.parent / "outputs" / "nominal" / "paper",
        )

        self.assertEqual(path, config_path.parent.parent / "outputs" / "nominal" / "paper" / "option_eps" / "eps")

    def test_run_scoped_subdir_does_not_duplicate_run_folder(self) -> None:
        config_path = Path(tempfile.mkdtemp()) / "configs" / "example.yaml"
        cfg = {"run_id": "nominal"}

        path = _resolve_run_scoped_subdir(
            config_path,
            cfg,
            "outputs/nominal/paper/option_eps/eps",
            default_name="eps",
            parent=config_path.parent.parent / "outputs" / "nominal" / "paper",
        )

        self.assertEqual(path, config_path.parent.parent / "outputs" / "nominal" / "paper" / "option_eps" / "eps")


if __name__ == "__main__":
    unittest.main()
