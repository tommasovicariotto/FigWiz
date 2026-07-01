from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from figwiz.publication import PublicationFigure, _legend_options, save_report_figure, write_latex_snippet
from figwiz.styles import REPORT_SIZE, get_publication_size


class PublicationTests(unittest.TestCase):
    def test_publication_sizes(self) -> None:
        self.assertEqual(get_publication_size("column").include_width, r"\columnwidth")
        self.assertEqual(get_publication_size("half_column").include_width, r"0.48\columnwidth")
        self.assertEqual(REPORT_SIZE.width_in, 6.2)

    def test_latex_snippet_contains_all_figures(self) -> None:
        output = Path(tempfile.mkdtemp()) / "figures.txt"
        figures = [
            PublicationFigure(
                name="tcp_position_error",
                eps_path=Path("tcp_position_error.eps"),
                x_label="time [s]",
                y_label="position error [cm]",
                caption="TCP position error",
                label="fig:tcp_position_error",
                size=get_publication_size("column"),
            ),
            PublicationFigure(
                name="kinetic_energy",
                eps_path=Path("kinetic_energy.eps"),
                x_label="time [s]",
                y_label="kinetic energy [J]",
                caption="Kinetic energy",
                label="fig:kinetic_energy",
                size=get_publication_size("half_column"),
            ),
        ]

        write_latex_snippet(figures, output)

        text = output.read_text(encoding="utf-8")
        self.assertIn(r"\usepackage{psfrag}", text)
        self.assertIn(r"\psfrag{XLABEL}", text)
        self.assertIn(r"\includegraphics[width=\columnwidth]{tcp_position_error.eps}", text)
        self.assertIn(r"\includegraphics[width=0.48\columnwidth]{kinetic_energy.eps}", text)
        self.assertEqual(text.count(r"\begin{figure}[t]"), 2)

    def test_legend_options(self) -> None:
        self.assertEqual(_legend_options(False, n_lines=3)["show"], False)
        self.assertEqual(_legend_options(True, n_lines=3)["columns"], 3)
        self.assertEqual(_legend_options({"columns": 2, "location": "upper right"}, n_lines=6)["columns"], 2)
        self.assertEqual(
            _legend_options({"columns": 2, "location": "upper right"}, n_lines=6)["location"],
            "upper right",
        )

    def test_report_export_has_no_plot_title(self) -> None:
        output_dir = Path(tempfile.mkdtemp())

        pdf_path = save_report_figure(
            x=np.arange(3),
            signal=np.arange(3),
            figure_cfg={"name": "kinetic_energy", "title": "Kinetic energy", "x_label": "time [s]", "y_label": "J"},
            signal_cfg={},
            output_dir=output_dir,
        )

        self.assertTrue(pdf_path.exists())


if __name__ == "__main__":
    unittest.main()
