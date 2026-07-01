from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicationSize:
    name: str
    width_in: float
    height_in: float
    include_width: str


@dataclass(frozen=True)
class PublicationStyle:
    font_size: float = 7.0
    tick_size: float = 6.0
    label_size: float = 7.0
    legend_size: float = 6.0
    line_width: float = 0.8
    axis_line_width: float = 0.6
    grid_line_width: float = 0.35


IEEE_RAL_STYLE = PublicationStyle()

PUBLICATION_SIZES: dict[str, PublicationSize] = {
    "column": PublicationSize(
        name="column",
        width_in=3.45,
        height_in=1.15,
        include_width=r"\columnwidth",
    ),
    "half_column": PublicationSize(
        name="half_column",
        width_in=1.65,
        height_in=0.95,
        include_width=r"0.48\columnwidth",
    ),
}


def get_publication_size(name: str | None) -> PublicationSize:
    if name is None:
        return PUBLICATION_SIZES["column"]
    if name not in PUBLICATION_SIZES:
        available = ", ".join(sorted(PUBLICATION_SIZES))
        raise ValueError(f"Unknown paper_size '{name}'. Available: {available}.")
    return PUBLICATION_SIZES[name]
