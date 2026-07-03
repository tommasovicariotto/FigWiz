from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import plotly.graph_objects as go

from figwiz.plotly_viewer import save_dashboard, save_or_show


class PlotlyViewerTests(unittest.TestCase):
    def test_dashboard_opens_with_default_browser_handler(self) -> None:
        output = Path(tempfile.mkdtemp()) / "dashboard.html"

        with patch("figwiz.plotly_viewer.webbrowser.open_new_tab") as open_new_tab:
            save_dashboard([("example", go.Figure())], output, open_browser=True)

        open_new_tab.assert_called_once_with(output.resolve().as_uri())

    def test_single_html_opens_with_default_browser_handler(self) -> None:
        output = Path(tempfile.mkdtemp()) / "figure.html"

        with patch("figwiz.plotly_viewer.webbrowser.open_new_tab") as open_new_tab:
            save_or_show(go.Figure(), output, open_browser=True)

        open_new_tab.assert_called_once_with(output.resolve().as_uri())


if __name__ == "__main__":
    unittest.main()
