from __future__ import annotations

from typing import Any

import pandas as pd

from app.features.normalization import clamp01

try:
    import pandas_ta as ta
except Exception:  # pragma: no cover
    ta = None


def _to_df(ohlcv: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv)
    if df.empty:
        return df

    columns_map = {
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
    }
    df = df.rename(columns=columns_map)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["close", "volume"])


def compute_ta_snapshot(ohlcv: list[dict[str, Any]]) -> dict[str, float]:
    df = _to_df(ohlcv)
    if df.empty or len(df) < 35:
        return {
            "momentum": 0.0,
            "technical_structure": 0.0,
            "overextension": 0.0,
            "momentum_loss": 0.0,
            "rv_volume": 0.0,
        }

    close = df["close"]
    volume = df["volume"]
    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma_20
    vwap = (close * volume).cumsum().iloc[-1] / max(volume.cumsum().iloc[-1], 1e-9)
    rv_volume = (volume.iloc[-1] / max(volume.rolling(20).mean().iloc[-1], 1e-9))

    if ta is not None:
        rsi = float(ta.rsi(close, length=14).iloc[-1])
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        macd_val = float(macd_df.iloc[-1, 0]) if macd_df is not None else 0.0
        macd_sig = float(macd_df.iloc[-1, 2]) if macd_df is not None else 0.0
    else:
        delta = close.diff().fillna(0)
        gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss = -delta.clip(upper=0).rolling(14).mean().iloc[-1]
        rs = gain / max(loss, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        macd_val = float(close.ewm(span=12).mean().iloc[-1] - close.ewm(span=26).mean().iloc[-1])
        macd_sig = float((close.ewm(span=12).mean() - close.ewm(span=26).mean()).ewm(span=9).mean().iloc[-1])

    trend_up = 1.0 if close.iloc[-1] > sma_20 > (sma_50 or sma_20) else 0.0
    momentum = clamp01((rsi - 45) / 30) * 0.55 + clamp01((macd_val - macd_sig) / max(abs(macd_sig) + 1e-9, 1e-9)) * 0.45
    technical_structure = clamp01(trend_up * 0.6 + clamp01((close.iloc[-1] - vwap) / max(vwap, 1e-9)) * 0.4)

    overextension = clamp01((rsi - 70) / 20) * 0.6 + clamp01((close.iloc[-1] - vwap) / max(vwap, 1e-9) / 0.15) * 0.4
    momentum_loss = clamp01((macd_sig - macd_val) / max(abs(macd_sig) + 1e-9, 1e-9))

    return {
        "momentum": float(momentum),
        "technical_structure": float(technical_structure),
        "overextension": float(overextension),
        "momentum_loss": float(momentum_loss),
        "rv_volume": float(clamp01(rv_volume / 3.0)),
    }
