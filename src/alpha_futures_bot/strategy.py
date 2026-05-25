"""Broker-free V1 trend pullback signal generation."""

from __future__ import annotations

from math import isfinite
from typing import Sequence

from alpha_futures_bot.config import default_config
from alpha_futures_bot.indicators import IndicatorSnapshot, calculate_indicators
from alpha_futures_bot.models import Candle, Regime, Side, Signal, SignalAction, Symbol
from alpha_futures_bot.regime import detect_regime

TREND_ALIGNMENT_POINTS = 25
VWAP_ALIGNMENT_POINTS = 20
PULLBACK_QUALITY_POINTS = 20
ATR_VALIDITY_POINTS = 15
VOLUME_CONFIRMATION_POINTS = 10
CANDLE_CONFIRMATION_POINTS = 10


def generate_signal(candles: Sequence[Candle]) -> Signal:
    """Return a signal object only; this function never places or routes orders."""

    snapshot = calculate_indicators(candles)
    regime = detect_regime(snapshot)
    if snapshot is None or regime is Regime.NO_TRADE or not candles:
        return _no_trade("indicators unavailable or regime is no-trade")

    last_candle = candles[-1]
    if regime is Regime.BULL_TREND:
        score = _score_long(snapshot, last_candle)
        if score >= default_config().risk.min_signal_score:
            entry_price = snapshot.last_close
            return Signal(
                symbol=Symbol.BTC,
                action=SignalAction.BUY,
                side=Side.LONG,
                score=score,
                reason="bull trend pullback",
                entry_price=entry_price,
                stop_loss=entry_price - (1.5 * snapshot.atr),
                take_profit=entry_price + (3.0 * snapshot.atr),
            )
        return _no_trade("long pullback score below threshold", score)

    if regime is Regime.BEAR_TREND:
        score = _score_short(snapshot, last_candle)
        if score >= default_config().risk.min_signal_score:
            entry_price = snapshot.last_close
            return Signal(
                symbol=Symbol.BTC,
                action=SignalAction.SELL,
                side=Side.SHORT,
                score=score,
                reason="bear trend pullback",
                entry_price=entry_price,
                stop_loss=entry_price + (1.5 * snapshot.atr),
                take_profit=entry_price - (3.0 * snapshot.atr),
            )
        return _no_trade("short pullback score below threshold", score)

    return _no_trade("unclear regime")


def _score_long(snapshot: IndicatorSnapshot, candle: Candle) -> float:
    score = 0
    pullback_band = 0.5 * snapshot.atr
    if snapshot.last_close > snapshot.ema_trend and snapshot.ema_fast > snapshot.ema_slow:
        score += TREND_ALIGNMENT_POINTS
    if snapshot.last_close >= snapshot.vwap - (0.25 * snapshot.atr):
        score += VWAP_ALIGNMENT_POINTS
    if abs(snapshot.last_close - snapshot.ema_fast) <= pullback_band:
        score += PULLBACK_QUALITY_POINTS
    if _atr_is_valid(snapshot):
        score += ATR_VALIDITY_POINTS
    if snapshot.last_volume >= snapshot.volume_average:
        score += VOLUME_CONFIRMATION_POINTS
    if candle.close > candle.open:
        score += CANDLE_CONFIRMATION_POINTS
    return _clamp_score(score)


def _score_short(snapshot: IndicatorSnapshot, candle: Candle) -> float:
    score = 0
    pullback_band = 0.5 * snapshot.atr
    if snapshot.last_close < snapshot.ema_trend and snapshot.ema_fast < snapshot.ema_slow:
        score += TREND_ALIGNMENT_POINTS
    if snapshot.last_close <= snapshot.vwap + (0.25 * snapshot.atr):
        score += VWAP_ALIGNMENT_POINTS
    if abs(snapshot.last_close - snapshot.ema_fast) <= pullback_band:
        score += PULLBACK_QUALITY_POINTS
    if _atr_is_valid(snapshot):
        score += ATR_VALIDITY_POINTS
    if snapshot.last_volume >= snapshot.volume_average:
        score += VOLUME_CONFIRMATION_POINTS
    if candle.close < candle.open:
        score += CANDLE_CONFIRMATION_POINTS
    return _clamp_score(score)


def _atr_is_valid(snapshot: IndicatorSnapshot) -> bool:
    return isfinite(snapshot.atr) and snapshot.atr > 0


def _clamp_score(score: float) -> float:
    return float(max(0, min(100, score)))


def _no_trade(reason: str, score: float = 0.0) -> Signal:
    return Signal(
        symbol=Symbol.BTC,
        action=SignalAction.NO_TRADE,
        score=_clamp_score(score),
        reason=reason,
    )
