from __future__ import annotations

from typing import Any

import numpy as np


def sample_time_axis(n_samples: int, fs: float) -> np.ndarray:
    if fs <= 0:
        raise ValueError("fs must be positive.")
    return np.arange(n_samples) / float(fs)


def downsample_step(fs: float, target_fs: float | bool | None) -> int:
    if target_fs is False or target_fs is None:
        return 1
    if fs <= 0:
        raise ValueError("fs must be positive.")
    if target_fs <= 0:
        raise ValueError("target_fs must be positive.")
    if fs <= target_fs:
        return 1
    return max(1, int(np.ceil(fs / float(target_fs))))


def downsample_signal(signal: np.ndarray, step: int) -> np.ndarray:
    if step <= 1:
        return signal
    return signal[::step]


def downsample_time_and_signal(time: np.ndarray, signal: np.ndarray, target_fs: float | bool | None) -> tuple[np.ndarray, np.ndarray]:
    fs = estimate_fs(time)
    if fs <= 0:
        return time, signal
    step = downsample_step(fs, target_fs)
    if step <= 1:
        return time, signal
    return time[::step], signal[::step]


def estimate_fs(time: np.ndarray) -> float:
    time = ensure_time_vector(time)
    if time.size < 2:
        return 0.0
    diffs = np.diff(time)
    positive_diffs = diffs[diffs > 0]
    if positive_diffs.size == 0:
        return 0.0
    return float(1.0 / np.median(positive_diffs))


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


def apply_processing(
    time: np.ndarray,
    signal: np.ndarray,
    processing: dict[str, Any] | None,
    *,
    sample_down: float | bool | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    processing = processing or {}
    time, signal = align_time_and_signal(time, signal)

    if "crop" in processing:
        time, signal = crop(time, signal, processing["crop"])

    if "scale" in processing:
        signal = scale(signal, processing["scale"])

    if processing.get("norm", False):
        signal = vector_norm(signal)

    time, signal = downsample_time_and_signal(time, signal, sample_down)
    return time, signal


def crop_array(signal: np.ndarray, window: list[float] | tuple[float, float], fs: float) -> tuple[np.ndarray, float]:
    if len(window) != 2:
        raise ValueError("crop must be [start, end].")
    time = sample_time_axis(signal.shape[0], fs)
    start, end = float(window[0]), float(window[1])
    mask = (time >= start) & (time <= end)
    cropped_time = time[mask]
    offset = float(cropped_time[0]) if cropped_time.size else start
    return signal[mask], offset


def apply_array_processing(
    signal: np.ndarray,
    processing: dict[str, Any] | None,
    *,
    fs: float,
    sample_down: float | bool | None = None,
) -> tuple[np.ndarray, float, float]:
    processing = processing or {}
    signal = np.asarray(signal)
    time_offset = 0.0

    if "crop" in processing:
        signal, time_offset = crop_array(signal, processing["crop"], fs)

    if "scale" in processing:
        signal = scale(signal, processing["scale"])

    if processing.get("norm", False):
        signal = vector_norm(signal)

    step = downsample_step(fs, sample_down)
    signal = downsample_signal(signal, step)
    return signal, float(fs) / step, time_offset
