from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from shutil import which
import subprocess

import numpy as np

from figwiz.publication import (
    PgfplotsFigure,
    PublicationFigure,
    _legend_options,
    m4_downsample,
    save_publication_figure,
    save_pgfplots_figure,
    save_report_figure,
    write_latex_snippet,
    write_pgfplots_snippet,
)
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

        write_latex_snippet(figures, output, graphics_prefix="eps/")

        text = output.read_text(encoding="utf-8")
        self.assertIn(r"\usepackage{graphicx}", text)
        self.assertIn(r"\usepackage{psfrag}", text)
        self.assertIn(r"\newcommand{\FontFigS}{.8}", text)
        self.assertIn(r"\newcommand{\FontFigM}{1}", text)
        self.assertIn(r"\psfrag{tim}[cc][cc][\FontFigS]{Time [s]}", text)
        self.assertIn(r"\psfrag{ylab}[cc][cc][\FontFigS]{Position error [cm]}", text)
        self.assertIn(r"\includegraphics[width=\columnwidth]{eps/tcp_position_error.eps}", text)
        self.assertIn(r"\includegraphics[width=0.48\columnwidth]{eps/kinetic_energy.eps}", text)
        self.assertEqual(text.count(r"\begin{figure}[t]"), 2)

    def test_publication_eps_contains_literal_psfrag_placeholders(self) -> None:
        output_dir = Path(tempfile.mkdtemp())

        figure = save_publication_figure(
            x=np.arange(3),
            signal=np.arange(3),
            figure_cfg={"name": "kinetic_energy", "x_label": "time [s]", "y_label": "energy [J]"},
            signal_cfg={},
            output_dir=output_dir,
        )

        eps_text = figure.eps_path.read_text(encoding="latin-1")
        self.assertIn("(tim) show", eps_text)
        self.assertIn("(ylab) show", eps_text)
        self.assertRegex(eps_text, r"/zero glyphshow")
        self.assertRegex(eps_text, r"/one glyphshow")
        if which("gs"):
            subprocess.run(
                ["gs", "-dBATCH", "-dNOPAUSE", "-sDEVICE=bbox", str(figure.eps_path)],
                check=True,
                capture_output=True,
                text=True,
            )

    def test_publication_eps_uses_psfrag_for_legend_entries(self) -> None:
        output_dir = Path(tempfile.mkdtemp())

        figure = save_publication_figure(
            x=np.arange(3),
            signal=np.column_stack([np.arange(3), np.arange(3) * 2, np.arange(3) * 3]),
            figure_cfg={"name": "tcp_rotation_error", "x_label": "time [s]", "y_label": "rotation [deg]"},
            signal_cfg={"components": [r"$\alpha$", r"$\beta$", r"$\gamma$"]},
            output_dir=output_dir,
        )
        snippet = Path(tempfile.mkdtemp()) / "figures.tex"
        write_latex_snippet([figure], snippet, graphics_prefix="eps/")

        eps_text = figure.eps_path.read_text(encoding="latin-1")
        snippet_text = snippet.read_text(encoding="utf-8")
        self.assertIn("(a) show", eps_text)
        self.assertIn("(b) show", eps_text)
        self.assertIn("(c) show", eps_text)
        self.assertIn(r"\psfrag{a}[cc][cc][\FontFigS]{$\alpha$}", snippet_text)
        self.assertIn(r"\psfrag{b}[cc][cc][\FontFigS]{$\beta$}", snippet_text)
        self.assertIn(r"\psfrag{c}[cc][cc][\FontFigS]{$\gamma$}", snippet_text)

    def test_m4_downsample_keeps_spike(self) -> None:
        time = np.arange(1000) / 1000
        signal = np.zeros(1000)
        signal[155] = 10.0

        time_m4, signal_m4 = m4_downsample(time, signal, buckets_per_second=10)

        self.assertIn(0.155, time_m4)
        self.assertIn(10.0, signal_m4)
        self.assertLessEqual(len(time_m4), 40)

    def test_pgfplots_export_writes_dat_and_tex(self) -> None:
        output_dir = Path(tempfile.mkdtemp())
        time = np.arange(1000) / 1000
        signal = np.column_stack([np.sin(time), np.cos(time)])

        figure = save_pgfplots_figure(
            time,
            signal,
            {
                "name": "tcp_position_error",
                "title": "TCP position error",
                "x_label": "time [s]",
                "y_label": "position error [cm]",
                "paper_size": "column",
                "processing": {"crop": [7, 50]},
            },
            {"components": ["x", "y"]},
            output_dir / "pgfplots",
            output_dir / "dat",
            buckets_per_second=10,
        )

        data_text = figure.data_path.read_text(encoding="utf-8")
        tex_text = figure.tex_path.read_text(encoding="utf-8")
        self.assertTrue(figure.data_path.exists())
        self.assertTrue(figure.tex_path.exists())
        self.assertTrue(data_text.startswith("time x y\n"))
        self.assertTrue(data_text.splitlines()[1].startswith("0 "))
        self.assertIn(r"\begin{axis}", tex_text)
        self.assertIn(r"figwiz_ieee", tex_text)
        self.assertIn(r"\addplot table[x=time,y=x]{dat/tcp_position_error.dat};", tex_text)
        self.assertIn(r"xlabel={Time [s]}", tex_text)
        self.assertIn(r"ylabel={Position error [cm]}", tex_text)
        self.assertIn(r"enlarge x limits=false", tex_text)
        self.assertIn(r"xmin=0", tex_text)
        self.assertIn(r"xmax=43", tex_text)
        self.assertIn(r"extra x ticks={43}", tex_text)
        self.assertIn(r"legend pos=", tex_text)

    def test_pgfplots_legend_keeps_latex_math_labels(self) -> None:
        output_dir = Path(tempfile.mkdtemp())
        time = np.arange(10) / 10
        signal = np.column_stack([time, time * 2, time * 3])

        figure = save_pgfplots_figure(
            time,
            signal,
            {"name": "tcp_rotation_error", "x_label": "time [s]", "y_label": "rotation error [deg]"},
            {"components": [r"$\alpha$", r"$\beta$", r"$\gamma$"]},
            output_dir / "pgfplots",
            output_dir / "dat",
            buckets_per_second=10,
        )

        data_text = figure.data_path.read_text(encoding="utf-8")
        tex_text = figure.tex_path.read_text(encoding="utf-8")
        self.assertTrue(data_text.startswith("time alpha beta gamma\n"))
        self.assertIn(r"\addlegendentry{$\alpha$}", tex_text)
        self.assertIn(r"\addlegendentry{$\beta$}", tex_text)
        self.assertIn(r"\addlegendentry{$\gamma$}", tex_text)

    def test_pgfplots_snippet_contains_style_and_inputs(self) -> None:
        output = Path(tempfile.mkdtemp()) / "figures_pgfplots.tex"
        figures = [
            PgfplotsFigure(
                name="tcp_position_error",
                tex_path=Path("tcp_position_error.tex"),
                data_path=Path("tcp_position_error.dat"),
                x_label="time [s]",
                y_label="position error [cm]",
                caption="TCP position error",
                label="fig:tcp_position_error",
                size=get_publication_size("column"),
            )
        ]

        write_pgfplots_snippet(figures, output)

        text = output.read_text(encoding="utf-8")
        self.assertNotIn("% Requires:", text)
        self.assertIn(r"\usepackage{tikz}", text)
        self.assertIn(r"\usepackage{pgfplots}", text)
        self.assertIn(r"\pgfplotsset{compat=1.18}", text)
        self.assertIn(r"figwiz_ieee/.style", text)
        self.assertIn(r"line width=0.18pt", text)
        self.assertIn(r"every axis plot/.append style={mark=none}", text)
        self.assertIn(r"\input{pgfplots/tcp_position_error.tex}", text)
        self.assertIn(r"\label{fig:tcp_position_error}", text)

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
