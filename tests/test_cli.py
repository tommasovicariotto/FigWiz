from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import typer

from figwiz.cli import _clean_output_dir, _resolve_run_scoped_subdir


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

    def test_clean_output_dir_removes_directory(self) -> None:
        path = Path(tempfile.mkdtemp()) / "paper"
        path.mkdir()
        stale = path / "stale.txt"
        stale.write_text("old", encoding="utf-8")

        _clean_output_dir(path)

        self.assertFalse(path.exists())

    def test_clean_output_dir_rejects_file(self) -> None:
        path = Path(tempfile.mkdtemp()) / "paper"
        path.write_text("not a directory", encoding="utf-8")

        with self.assertRaises(typer.BadParameter):
            _clean_output_dir(path)


if __name__ == "__main__":
    unittest.main()
