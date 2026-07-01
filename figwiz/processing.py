from __future__ import annotations

from typing import Any

import numpy as np


def sample_time_axis(n_samples: int, fs: float) -> np.ndarray:
    if fs <= 0:
        raise ValueError("fs must be positive.")
    return np.arange(n_samples) / float(fs)


def ensure_time_vector(time: np.ndarray) -> np.ndarray:
    time = np.asarray(time).squeeze()
    if time.ndim != 1:
        raise ValueError(f"Time signal must be 1D after squeezing. Got shape {time.shape}.")
    return time


def align_time_and_signal(time: np.ndarray, signal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    time = ensure_time_vector(time)
    signal = np.asarray(signal)

    if signal.ndim == 1:
        if signal.shape[0] != time.shape[0]:
            raise ValueError(f"Signal length {signal.shape[0]} does not match time length {time.shape[0]}.")
        return time, signal

    if signal.shape[0] == time.shape[0]:
        return time, signal

    if signal.shape[-1] == time.shape[0]:
        return time, signal.T

    raise ValueError(f"Cannot align signal shape {signal.shape} with time length {time.shape[0]}.")


def crop(time: np.ndarray, signal: np.ndarray, window: list[float] | tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    if len(window) != 2:
        raise ValueError("crop must be [start, end].")
    start, end = float(window[0]), float(window[1])
    mask = (time >= start) & (time <= end)
    return time[mask], signal[mask]


def scale(signal: np.ndarray, factor: float) -> np.ndarray:
    return signal * float(factor)


def vector_norm(signal: np.ndarray) -> np.ndarray:
    signal = np.asarray(signal)
    if signal.ndim == 1:
        return np.abs(signal)
    return np.linalg.norm(signal, axis=1)


def apply_processing(time: np.ndarray, signal: np.ndarray, processing: dict[str, Any] | None) -> tuple[np.ndarray, np.ndarray]:
    processing = processing or {}
    time, signal = align_time_and_signal(time, signal)

    if "crop" in processing:
        time, signal = crop(time, signal, processing["crop"])

    if "scale" in processing:
        signal = scale(signal, processing["scale"])

    if processing.get("norm", False):
        signal = vector_norm(signal)

    return time, signal


def crop_array(signal: np.ndarray, window: list[float] | tuple[float, float]) -> np.ndarray:
    if len(window) != 2:
        raise ValueError("crop must be [start, end].")
    start, end = int(window[0]), int(window[1])
    return signal[start : end + 1]


def apply_array_processing(signal: np.ndarray, processing: dict[str, Any] | None) -> np.ndarray:
    processing = processing or {}
    signal = np.asarray(signal)

    if "crop" in processing:
        signal = crop_array(signal, processing["crop"])

    if "scale" in processing:
        signal = scale(signal, processing["scale"])

    if processing.get("norm", False):
        signal = vector_norm(signal)

    return signal
