from __future__ import annotations

from alpha_futures_bot.indicators import IndicatorSnapshot, calculate_indicators
from alpha_futures_bot.models import Regime
from alpha_futures_bot.presets import LOOSE_PRESET, STRICT_PRESET
from alpha_futures_bot.regime import detect_regime


def test_valid_bullish_snapshot_returns_bull_trend() -> None:
    from conftest import make_bullish_pullback_candles

    assert detect_regime(calculate_indicators(make_bullish_pullback_candles())) is Regime.BULL_TREND


def test_valid_bearish_snapshot_returns_bear_trend() -> None:
    from conftest import make_bearish_pullback_candles

    assert detect_regime(calculate_indicators(make_bearish_pullback_candles())) is Regime.BEAR_TREND


def test_mixed_conditions_return_no_trade() -> None:
    snapshot = IndicatorSnapshot(
        ema_fast=105.0,
        ema_slow=100.0,
        ema_trend=110.0,
        vwap=100.0,
        atr=2.0,
        volume_average=100.0,
        last_close=101.0,
        last_volume=100.0,
    )

    assert detect_regime(snapshot) is Regime.NO_TRADE


def test_missing_or_invalid_snapshot_returns_no_trade() -> None:
    invalid = IndicatorSnapshot(
        ema_fast=105.0,
        ema_slow=100.0,
        ema_trend=90.0,
        vwap=100.0,
        atr=0.0,
        volume_average=100.0,
        last_close=106.0,
        last_volume=100.0,
    )

    assert detect_regime(None) is Regime.NO_TRADE
    assert detect_regime(invalid) is Regime.NO_TRADE


def test_flat_equal_boundaries_return_no_trade() -> None:
    snapshot = IndicatorSnapshot(
        ema_fast=100.0,
        ema_slow=100.0,
        ema_trend=100.0,
        vwap=100.0,
        atr=2.0,
        volume_average=100.0,
        last_close=100.0,
        last_volume=100.0,
    )

    assert detect_regime(snapshot) is Regime.NO_TRADE


def test_custom_regime_vwap_tolerance_changes_classification() -> None:
    snapshot = IndicatorSnapshot(
        ema_fast=105.0,
        ema_slow=100.0,
        ema_trend=90.0,
        vwap=100.0,
        atr=2.0,
        volume_average=100.0,
        last_close=99.4,
        last_volume=100.0,
    )

    assert detect_regime(snapshot, STRICT_PRESET) is Regime.NO_TRADE
    assert detect_regime(snapshot, LOOSE_PRESET) is Regime.BULL_TREND
