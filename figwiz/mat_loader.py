from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


MATLAB_INTERNAL_KEYS = {"__header__", "__version__", "__globals__"}


def load_mat_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MAT file not found: {path}")

    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    return {k: v for k, v in raw.items() if k not in MATLAB_INTERNAL_KEYS}


def variable_summary(mat_data: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows = []
    for name, value in sorted(mat_data.items()):
        shape = getattr(value, "shape", "scalar")
        dtype = getattr(value, "dtype", type(value).__name__)
        rows.append((name, str(shape), str(dtype)))
    return rows


def as_array(value: Any, name: str) -> np.ndarray:
    try:
        arr = np.asarray(value)
    except Exception as exc:
        raise TypeError(f"Could not convert variable '{name}' to numpy array.") from exc

    if arr.dtype == object:
        raise TypeError(
            f"Variable '{name}' looks like a MATLAB object/struct. "
            "FigWiz supports numeric arrays and time-series data."
        )

    arr = np.squeeze(arr)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr
