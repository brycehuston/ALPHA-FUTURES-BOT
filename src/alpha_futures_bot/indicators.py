"""Deterministic V1 indicators for BTC-only offline analysis."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import fmean
from typing import Sequence

from alpha_futures_bot.models import Candle, Symbol

EMA_FAST_PERIOD = 21
EMA_SLOW_PERIOD = 50
EMA_TREND_PERIOD = 200
ATR_PERIOD = 14
VOLUME_AVG_PERIOD = 20
VWAP_WINDOW = 20


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    """Complete indicator state required by Phase 2 regime and strategy logic."""

    ema_fast: float
    ema_slow: float
    ema_trend: float
    vwap: float
    atr: float
    volume_average: float
    last_close: float
    last_volume: float


def calculate_indicators(candles: Sequence[Candle]) -> IndicatorSnapshot | None:
    """Calculate V1 indicators, returning None when inputs are not safely usable."""

    if len(candles) < EMA_TREND_PERIOD:
        return None
    if not _candles_are_valid(candles):
        return None

    closes = [candle.close for candle in candles]
    ema_fast = _ema(closes, EMA_FAST_PERIOD)
    ema_slow = _ema(closes, EMA_SLOW_PERIOD)
    ema_trend = _ema(closes, EMA_TREND_PERIOD)
    vwap = _vwap(candles[-VWAP_WINDOW:])
    atr = _atr(candles)
    volume_average = fmean(candle.volume for candle in candles[-VOLUME_AVG_PERIOD:])

    values = (
        ema_fast,
        ema_slow,
        ema_trend,
        vwap,
        atr,
        volume_average,
        candles[-1].close,
        candles[-1].volume,
    )
    if any(not _finite(value) for value in values):
        return None

    return IndicatorSnapshot(
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        ema_trend=ema_trend,
        vwap=vwap,
        atr=atr,
        volume_average=volume_average,
        last_close=candles[-1].close,
        last_volume=candles[-1].volume,
    )


def _ema(values: Sequence[float], period: int) -> float:
    multiplier = 2.0 / (period + 1.0)
    ema_value = values[0]
    for value in values[1:]:
        ema_value = ((value - ema_value) * multiplier) + ema_value
    return ema_value


def _vwap(candles: Sequence[Candle]) -> float:
    volume_sum = sum(candle.volume for candle in candles)
    if volume_sum <= 0:
        return float("nan")
    weighted_price_sum = sum(_typical_price(candle) * candle.volume for candle in candles)
    return weighted_price_sum / volume_sum


def _atr(candles: Sequence[Candle]) -> float:
    ranges = []
    start = len(candles) - ATR_PERIOD
    for index in range(start, len(candles)):
        candle = candles[index]
        previous_close = candles[index - 1].close
        ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )
    return fmean(ranges)


def _typical_price(candle: Candle) -> float:
    return (candle.high + candle.low + candle.close) / 3.0


def _candles_are_valid(candles: Sequence[Candle]) -> bool:
    for candle in candles:
        if candle.symbol is not Symbol.BTC:
            return False
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if any(not _finite(value) for value in values):
            return False
        if min(candle.open, candle.high, candle.low, candle.close) <= 0:
            return False
        if candle.volume < 0:
            return False
        if candle.high < candle.low:
            return False
        if candle.high < max(candle.open, candle.close):
            return False
        if candle.low > min(candle.open, candle.close):
            return False
    return True


def _finite(value: float) -> bool:
    return isfinite(value)
