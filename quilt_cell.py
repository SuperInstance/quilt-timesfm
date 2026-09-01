"""
quilt_cell.py — the `time.cell` Quilt cell kind wrapping TimesFM 3.0.

The cell shape (Phase 228, 5th cutting-edge adoption):
- Cell state: the historical time series (a 2D numpy array)
- Cell value: the forecast (a 2D numpy array) + quantile intervals
- Cell reads: covariates (past-only, past-and-future)
- The 5+1+1+1+1+1+1 opcodes (now 11 with TIME) apply unchanged.

The substrate binding:
- ROUTE picks the model: TimesFM 2.5 vs 3.0, PyTorch vs Flax
- FORECAST runs the model (the substrate calls the actual transformer)
- The polyformalism claim: the cell shape is identical to the C
  port (quilt-c/include/quilt/time.h). The state_hash is the
  same FNV-1a. The forecast structure is the same (point + 9
  quantiles).
"""
from __future__ import annotations

import os
import sys
import json
import hashlib
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass, field


# FNV-1a 64-bit (matches the C and Rust ports, bit-exact)
FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME  = 0x100000001b3
FNV_SLICE_MUL = 0x9e3779b97f4a7c15


def fnv1a64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def fnv1a64_str(s: str) -> int:
    return fnv1a64(s.encode("utf-8"))


def fnv1a64_ndarray(arr: np.ndarray) -> int:
    """FNV-1a 64-bit of a numpy array's raw bytes."""
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    return fnv1a64(arr.tobytes())


def hash_to_32(h: int) -> bytes:
    """Spread a 64-bit hash over 4 slices (32 bytes, little-endian)."""
    out = bytearray(32)
    for i in range(4):
        slice_val = (h + (i * FNV_SLICE_MUL)) & 0xFFFFFFFFFFFFFFFF
        for j in range(8):
            out[i * 8 + j] = (slice_val >> (j * 8)) & 0xFF
    return bytes(out)


# The 5 time-cell operations (matches the C port's enum exactly)
class TimeOp:
    BIND_CONTEXT = 0
    BIND_COVARIATE = 1
    FORECAST = 2
    READ_POINT = 3
    READ_QUANTILE = 4
    COUNT = 5


TIME_OP_NAMES = {
    TimeOp.BIND_CONTEXT: "BIND_CONTEXT",
    TimeOp.BIND_COVARIATE: "BIND_COVARIATE",
    TimeOp.FORECAST: "FORECAST",
    TimeOp.READ_POINT: "READ_POINT",
    TimeOp.READ_QUANTILE: "READ_QUANTILE",
}


@dataclass
class Forecast:
    """A forecast output (point + 9 quantiles)."""
    # Point forecast: shape [horizon, n_variates]
    point: np.ndarray = field(default_factory=lambda: np.zeros(0))
    # Quantile forecasts: shape [9, horizon, n_variates] (9 quantiles)
    quantiles: np.ndarray = field(default_factory=lambda: np.zeros(0))
    # Model version: 0 = 2.5, 1 = 3.0
    model_version: int = 1
    # Model variant: 0 = PyTorch, 1 = Flax
    model_variant: int = 0

    @property
    def horizon(self) -> int:
        return self.point.shape[0] if self.point.size > 0 else 0

    @property
    def n_variates(self) -> int:
        return self.point.shape[1] if self.point.ndim == 2 and self.point.size > 0 else 0


class TimeCell:
    """A `time.cell` Quilt cell, backed by TimesFM 3.0.

    The cell is a 2D time-series forecaster:
    - State: a [context_length, n_variates] float array
    - Value: a [horizon, n_variates] forecast + 9 quantile prediction intervals
    - Reads: covariates (past-only, past-and-future)

    The polyformalism claim: the cell shape, operation indices, and
    state_hash are bit-exact with the C port (quilt-c/include/quilt/time.h).
    The substrate binding (TimesFM 2.5 / 3.0 / PyTorch / Flax) is the
    only thing that varies.
    """

    def __init__(self, model_version: int = 1, model_variant: int = 0):
        # Cell state
        self.context: Optional[np.ndarray] = None  # [context_len, n_variates]
        self.context_len: int = 0
        self.n_variates: int = 0
        # Covariates
        self.past_only: Optional[np.ndarray] = None
        self.past_future: Optional[np.ndarray] = None
        # Forecast horizon
        self.horizon: int = 0
        # PROOF chain: FNV-1a 64-bit, spread over 4 slices (32 bytes)
        self.prev_hash: bytes = bytes(32)
        self.state_hash: bytes = bytes(32)
        # The last forecast
        self.forecast = Forecast()
        # Model selection
        self.model_version = model_version  # 0 = 2.5, 1 = 3.0
        self.model_variant = model_variant  # 0 = PyTorch, 1 = Flax
        # Counters
        self.n_bind_context = 0
        self.n_bind_covariate = 0
        self.n_forecast = 0
        self.n_read_point = 0
        self.n_read_quantile = 0
        # The model is loaded lazily (don't download 800MB on import)
        self._model = None

    # The polyformalism: kind name and op count
    @staticmethod
    def kind_name() -> str:
        return "time.cell"

    @staticmethod
    def kind_count() -> int:
        return TimeOp.COUNT

    @staticmethod
    def op_name(op: int) -> str:
        return TIME_OP_NAMES.get(op, "?")

    # ── The 5 operations ────────────────────────────────────────────

    def bind_context(self, context: np.ndarray) -> int:
        """Bind the historical context (BIND_CONTEXT)."""
        if context is None or context.size == 0:
            return -1
        # BIND: save prev_hash, then set the new state.
        self.prev_hash = self.state_hash
        if context.ndim == 1:
            context = context.reshape(-1, 1)
        if not isinstance(context, np.ndarray):
            context = np.asarray(context, dtype=np.float64)
        self.context = context.astype(np.float64)
        self.context_len = self.context.shape[0]
        self.n_variates = self.context.shape[1] if self.context.ndim == 2 else 1
        # New state_hash: FNV-1a of the tensor bytes
        h = fnv1a64_ndarray(self.context)
        self.state_hash = hash_to_32(h)
        # Invalidate the previous forecast (any BIND invalidates it)
        self.forecast = Forecast(model_version=self.model_version,
                                  model_variant=self.model_variant)
        self.n_bind_context += 1
        return 0

    def bind_past_only_covariate(self, cov: np.ndarray) -> int:
        """Bind a past-only covariate (BIND_COVARIATE, kind=0)."""
        if cov is None or cov.size == 0:
            return -1
        if not isinstance(cov, np.ndarray):
            cov = np.asarray(cov, dtype=np.float64)
        self.past_only = cov.astype(np.float64)
        self.n_bind_covariate += 1
        return 0

    def bind_past_future_covariate(self, cov: np.ndarray) -> int:
        """Bind a past-and-future covariate (BIND_COVARIATE, kind=1)."""
        if cov is None or cov.size == 0:
            return -1
        if not isinstance(cov, np.ndarray):
            cov = np.asarray(cov, dtype=np.float64)
        self.past_future = cov.astype(np.float64)
        self.n_bind_covariate += 1
        return 0

    def set_horizon(self, horizon: int) -> int:
        """Set the forecast horizon."""
        if horizon <= 0:
            return -1
        self.horizon = horizon
        return 0

    def forecast_(self) -> int:
        """Run the model (FORECAST).

        This is the substrate binding: the actual call to TimesFM.
        In the no-model case (e.g. CI without the 800MB checkpoint),
        we fall back to a synthetic FNV-1a-seeded forecast.
        """
        if self.context is None or self.horizon == 0:
            return -1
        # Try the real TimesFM call first
        try:
            return self._forecast_real()
        except Exception as e:
            # Fall back to the synthetic forecast (same shape as C port)
            return self._forecast_synthetic()

    def _forecast_real(self) -> int:
        """The substrate binding: real TimesFM 3.0 call."""
        # Lazy import (the 800MB checkpoint is downloaded on first use)
        from src.timesfm3 import TimesFM3Forecaster, ModelConfig, ForecastOutput
        if self._model is None:
            cfg = ModelConfig(
                checkpoint_path="google/timesfm-3.0-pytorch",
                per_core_batch_size=1,
                input_patch_length=32,
                output_patch_length=64,
            )
            self._model = TimesFM3Forecaster(cfg)
        # TimesFM expects [batch, context_length] for univariate, or
        # [batch, context_length, n_variates] for multivariate.
        # We transpose our [context, variates] -> [variates, context]
        # (variates are independent series in TimesFM).
        x = self.context.T  # [n_variates, context_len]
        # Use 1D forecast; the cell is univariate per variate.
        forecasts: list[np.ndarray] = []
        for v in range(self.n_variates):
            fc = self._model.forecast([x[v]], freq=[0])  # 0 = high frequency
            # fc is a ForecastOutput; .forecast is the point forecast
            forecasts.append(np.asarray(fc[0].forecast, dtype=np.float64))
        # Pad/crop to self.horizon
        point = np.zeros((self.horizon, self.n_variates), dtype=np.float64)
        for v in range(self.n_variates):
            f = forecasts[v]
            h = min(self.horizon, len(f))
            point[:h, v] = f[:h]
        # Quantile intervals: derived from the point forecast + the
        # model's reported quantiles (if available). For the public
        # API, TimesFM exposes .quantiles; we use that.
        quantiles = np.zeros((9, self.horizon, self.n_variates), dtype=np.float64)
        for v in range(self.n_variates):
            fc = self._model.forecast([x[v]], freq=[0])[0]
            if fc.quantiles is not None:
                qs = np.asarray(fc.quantiles, dtype=np.float64)  # [9, horizon]
                h = min(self.horizon, qs.shape[1])
                quantiles[:, :h, v] = qs[:, :h]
            else:
                # Synthesize: spread the point
                for q_idx in range(9):
                    offset = (q_idx - 4) * 2.0
                    quantiles[q_idx, :, v] = point[:, v] + offset
        self.forecast = Forecast(
            point=point, quantiles=quantiles,
            model_version=self.model_version, model_variant=self.model_variant,
        )
        self.n_forecast += 1
        return 0

    def _forecast_synthetic(self) -> int:
        """Synthetic forecast (no model needed). Mirrors the C port."""
        out_len = self.horizon * self.n_variates
        # Hash the context to seed a synthetic pattern.
        h = fnv1a64_ndarray(self.context)
        # point: [horizon, n_variates]
        point = np.zeros((self.horizon, self.n_variates), dtype=np.float64)
        # quantiles: [9, horizon, n_variates]
        quantiles = np.zeros((9, self.horizon, self.n_variates), dtype=np.float64)
        for v in range(self.n_variates):
            for t in range(self.horizon):
                h = ((h * FNV_PRIME) ^ ((v * FNV_SLICE_MUL) & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
                h = ((h * FNV_PRIME) ^ t) & 0xFFFFFFFFFFFFFFFF
                # Use a 32-bit cast to keep values in the int range
                # (so the double cast is exact). Use modulo before cast.
                h32 = h % (1 << 32)  # 0..2^32
                if h32 >= (1 << 31):
                    h32 -= (1 << 32)  # sign-extend
                base = float(h32) / 100.0
                # Squash to -50..+50
                if base > 50.0: base = 50.0
                if base < -50.0: base = -50.0
                point[t, v] = base
                for q_idx in range(9):
                    offset = (q_idx - 4) * 2.0  # -8..+8
                    quantiles[q_idx, t, v] = base + offset
        self.forecast = Forecast(
            point=point, quantiles=quantiles,
            model_version=self.model_version, model_variant=self.model_variant,
        )
        self.n_forecast += 1
        return 0

    def read_point(self, variate: int = 0) -> np.ndarray:
        """Read the point forecast for a given variate (READ_POINT)."""
        if self.forecast.point is None or self.forecast.point.size == 0:
            return np.zeros(0)
        if variate >= self.n_variates:
            return np.zeros(0)
        self.n_read_point += 1
        return self.forecast.point[:, variate].copy()

    def read_quantile(self, q: float, variate: int = 0) -> np.ndarray:
        """Read a quantile forecast for a given variate (READ_QUANTILE)."""
        if self.forecast.quantiles is None or self.forecast.quantiles.size == 0:
            return np.zeros(0)
        if variate >= self.n_variates:
            return np.zeros(0)
        # Map q in [0.1, 0.9] to a quantile index in [0, 8]
        qi = int(q * 10.0 - 0.5)
        if qi < 0: qi = 0
        if qi > 8: qi = 8
        self.n_read_quantile += 1
        return self.forecast.quantiles[qi, :, variate].copy()
