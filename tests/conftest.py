"""Shared pytest helpers for Phase 1 safety tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from alpha_futures_bot.models import Candle, OrderRequest, Side, Signal, SignalAction, Symbol


@pytest.fixture
def valid_config_dict() -> Callable[[], dict[str, Any]]:
    def make_config() -> dict[str, Any]:
        return {
            "mode": "PAPER",
            "symbol": "BTC",
            "risk": {
                "max_position_notional": 10_000.0,
                "max_risk_per_trade_pct": 0.005,
                "min_signal_score": 70.0,
                "max_leverage": 1.0,
                "daily_max_loss_pct": 0.02,
                "max_open_positions": 1,
            },
        }

    return make_config


def make_candle(index: int, close: float, volume: float = 100.0, symbol: Symbol | str = Symbol.BTC) -> Candle:
    spread = 1.0
    open_price = close
    return Candle(
        symbol=symbol,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index),
        open=open_price,
        high=max(open_price, close) + spread,
        low=min(open_price, close) - spread,
        close=close,
        volume=volume,
    )


def make_bullish_pullback_candles() -> list[Candle]:
    candles = [make_candle(index, 100.0 + (index * 0.45), 100.0) for index in range(220)]
    last = candles[-1]
    candles[-1] = Candle(
        symbol=Symbol.BTC,
        timestamp=last.timestamp,
        open=192.5,
        high=194.5,
        low=191.5,
        close=193.5,
        volume=140.0,
    )
    return candles


def make_bearish_pullback_candles() -> list[Candle]:
    candles = [make_candle(index, 220.0 - (index * 0.45), 100.0) for index in range(220)]
    last = candles[-1]
    candles[-1] = Candle(
        symbol=Symbol.BTC,
        timestamp=last.timestamp,
        open=127.5,
        high=128.5,
        low=125.5,
        close=126.5,
        volume=140.0,
    )
    return candles


def make_flat_candles() -> list[Candle]:
    return [make_candle(index, 100.0, 100.0) for index in range(220)]


def make_too_short_candles() -> list[Candle]:
    return [make_candle(index, 100.0 + index, 100.0) for index in range(199)]


def make_long_signal() -> Signal:
    return Signal(
        symbol=Symbol.BTC,
        action=SignalAction.BUY,
        side=Side.LONG,
        score=80.0,
        reason="test long",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
    )


def make_short_signal() -> Signal:
    return Signal(
        symbol=Symbol.BTC,
        action=SignalAction.SELL,
        side=Side.SHORT,
        score=80.0,
        reason="test short",
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
    )


def make_long_order() -> OrderRequest:
    return OrderRequest(
        symbol=Symbol.BTC,
        side=Side.LONG,
        quantity=1.0,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
    )


def make_short_order() -> OrderRequest:
    return OrderRequest(
        symbol=Symbol.BTC,
        side=Side.SHORT,
        quantity=1.0,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
    )
