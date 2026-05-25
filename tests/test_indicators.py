from __future__ import annotations

from math import isclose

import pytest

from alpha_futures_bot.indicators import (
    ATR_PERIOD,
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
    EMA_TREND_PERIOD,
    VOLUME_AVG_PERIOD,
    VWAP_WINDOW,
    calculate_indicators,
)
from alpha_futures_bot.models import Candle, Symbol


def test_indicators_are_deterministic_for_flat_candles() -> None:
    from conftest import make_flat_candles

    snapshot = calculate_indicators(make_flat_candles())

    assert snapshot is not None
    assert snapshot.ema_fast == 100.0
    assert snapshot.ema_slow == 100.0
    assert snapshot.ema_trend == 100.0
    assert snapshot.vwap == 100.0
    assert snapshot.atr == 2.0
    assert snapshot.volume_average == 100.0
    assert snapshot.last_close == 100.0
    assert snapshot.last_volume == 100.0


def test_ema_fast_slow_and_trend_values_are_deterministic() -> None:
    from conftest import make_bullish_pullback_candles

    candles = make_bullish_pullback_candles()
    snapshot = calculate_indicators(candles)

    assert snapshot is not None
    closes = [candle.close for candle in candles]
    assert isclose(snapshot.ema_fast, _expected_ema(closes, EMA_FAST_PERIOD))
    assert isclose(snapshot.ema_slow, _expected_ema(closes, EMA_SLOW_PERIOD))
    assert isclose(snapshot.ema_trend, _expected_ema(closes, EMA_TREND_PERIOD))


def test_vwap_atr_and_volume_average_are_deterministic() -> None:
    from conftest import make_bullish_pullback_candles

    candles = make_bullish_pullback_candles()
    snapshot = calculate_indicators(candles)

    assert snapshot is not None
    assert isclose(snapshot.vwap, _expected_vwap(candles[-VWAP_WINDOW:]))
    assert isclose(snapshot.atr, _expected_atr(candles))
    assert isclose(
        snapshot.volume_average,
        sum(candle.volume for candle in candles[-VOLUME_AVG_PERIOD:]) / VOLUME_AVG_PERIOD,
    )


def test_fewer_than_ema_trend_period_candles_returns_none() -> None:
    from conftest import make_too_short_candles

    assert calculate_indicators(make_too_short_candles()) is None


@pytest.mark.parametrize(
    "field",
    ["open", "high", "low", "close", "volume"],
)
def test_bad_or_non_finite_ohlcv_returns_none(field: str) -> None:
    from conftest import make_flat_candles

    candles = make_flat_candles()
    bad = candles[-1]
    replacement = {
        "open": bad.open,
        "high": bad.high,
        "low": bad.low,
        "close": bad.close,
        "volume": bad.volume,
    }
    replacement[field] = float("nan")
    candles[-1] = Candle(symbol=bad.symbol, timestamp=bad.timestamp, **replacement)

    assert calculate_indicators(candles) is None


def test_zero_vwap_volume_window_returns_none() -> None:
    from conftest import make_flat_candles

    candles = make_flat_candles()
    for index in range(len(candles) - VWAP_WINDOW, len(candles)):
        candle = candles[index]
        candles[index] = Candle(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=0.0,
        )

    assert calculate_indicators(candles) is None


def test_non_btc_or_mixed_symbols_return_none() -> None:
    from conftest import make_flat_candles

    candles = make_flat_candles()
    bad = candles[-1]
    candles[-1] = Candle(
        symbol="ETH",
        timestamp=bad.timestamp,
        open=bad.open,
        high=bad.high,
        low=bad.low,
        close=bad.close,
        volume=bad.volume,
    )

    assert calculate_indicators(candles) is None


def _expected_ema(values: list[float], period: int) -> float:
    multiplier = 2.0 / (period + 1.0)
    ema = values[0]
    for value in values[1:]:
        ema = ((value - ema) * multiplier) + ema
    return ema


def _expected_vwap(candles: list[Candle]) -> float:
    weighted_sum = sum(((c.high + c.low + c.close) / 3.0) * c.volume for c in candles)
    volume_sum = sum(c.volume for c in candles)
    return weighted_sum / volume_sum


def _expected_atr(candles: list[Candle]) -> float:
    ranges = []
    for index in range(len(candles) - ATR_PERIOD, len(candles)):
        candle = candles[index]
        previous_close = candles[index - 1].close
        ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )
    return sum(ranges) / ATR_PERIOD
