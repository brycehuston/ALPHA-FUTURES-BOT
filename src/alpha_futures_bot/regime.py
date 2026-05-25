"""Conservative V1 regime detection."""

from __future__ import annotations

from math import isfinite

from alpha_futures_bot.indicators import IndicatorSnapshot
from alpha_futures_bot.models import Regime
from alpha_futures_bot.presets import StrategySettings, get_preset


def detect_regime(snapshot: IndicatorSnapshot | None, settings: StrategySettings | None = None) -> Regime:
    """Detect trend regime, preferring NO_TRADE for invalid or unclear states."""

    strategy_settings = get_preset(settings)
    if snapshot is None or not _snapshot_is_valid(snapshot):
        return Regime.NO_TRADE

    vwap_near_band = strategy_settings.regime_near_vwap_atr_multiplier * snapshot.atr
    bullish = (
        snapshot.last_close > snapshot.ema_trend
        and snapshot.ema_fast > snapshot.ema_slow
        and snapshot.last_close >= snapshot.vwap - vwap_near_band
    )
    bearish = (
        snapshot.last_close < snapshot.ema_trend
        and snapshot.ema_fast < snapshot.ema_slow
        and snapshot.last_close <= snapshot.vwap + vwap_near_band
    )

    if bullish and not bearish:
        return Regime.BULL_TREND
    if bearish and not bullish:
        return Regime.BEAR_TREND
    return Regime.NO_TRADE


def _snapshot_is_valid(snapshot: IndicatorSnapshot) -> bool:
    values = (
        snapshot.ema_fast,
        snapshot.ema_slow,
        snapshot.ema_trend,
        snapshot.vwap,
        snapshot.atr,
        snapshot.volume_average,
        snapshot.last_close,
        snapshot.last_volume,
    )
    if any(not isfinite(value) for value in values):
        return False
    if snapshot.atr <= 0 or snapshot.volume_average <= 0:
        return False
    if snapshot.ema_fast == snapshot.ema_slow:
        return False
    if snapshot.last_close == snapshot.ema_trend:
        return False
    return True
