from __future__ import annotations

from pathlib import Path

from alpha_futures_bot.models import Side, Signal, SignalAction
from alpha_futures_bot.indicators import calculate_indicators
from alpha_futures_bot.strategy import generate_signal


def test_bullish_pullback_can_produce_long_signal() -> None:
    from conftest import make_bullish_pullback_candles

    signal = generate_signal(make_bullish_pullback_candles())

    assert signal.action is SignalAction.BUY
    assert signal.side is Side.LONG
    assert signal.score >= 70.0
    snapshot = calculate_indicators(make_bullish_pullback_candles())
    assert snapshot is not None
    assert signal.entry_price == snapshot.last_close
    assert signal.stop_loss == snapshot.last_close - (1.5 * snapshot.atr)
    assert signal.take_profit == snapshot.last_close + (3.0 * snapshot.atr)


def test_bearish_pullback_can_produce_short_signal() -> None:
    from conftest import make_bearish_pullback_candles

    signal = generate_signal(make_bearish_pullback_candles())

    assert signal.action is SignalAction.SELL
    assert signal.side is Side.SHORT
    assert signal.score >= 70.0
    snapshot = calculate_indicators(make_bearish_pullback_candles())
    assert snapshot is not None
    assert signal.entry_price == snapshot.last_close
    assert signal.stop_loss == snapshot.last_close + (1.5 * snapshot.atr)
    assert signal.take_profit == snapshot.last_close - (3.0 * snapshot.atr)


def test_no_trade_regime_produces_no_trade_signal() -> None:
    from conftest import make_flat_candles

    signal = generate_signal(make_flat_candles())

    assert signal.action is SignalAction.NO_TRADE
    assert signal.side is None


def test_low_score_produces_no_trade_signal() -> None:
    from conftest import make_bullish_pullback_candles

    candles = make_bullish_pullback_candles()
    last = candles[-1]
    candles[-1] = type(last)(
        symbol=last.symbol,
        timestamp=last.timestamp,
        open=203.0,
        high=204.0,
        low=201.0,
        close=202.0,
        volume=1.0,
    )
    signal = generate_signal(candles)

    assert signal.action is SignalAction.NO_TRADE
    assert signal.score < 70.0


def test_insufficient_or_bad_candles_produce_no_trade_signal() -> None:
    from conftest import make_flat_candles, make_too_short_candles

    bad_candles = make_flat_candles()
    last = bad_candles[-1]
    bad_candles[-1] = type(last)(
        symbol=last.symbol,
        timestamp=last.timestamp,
        open=float("nan"),
        high=last.high,
        low=last.low,
        close=last.close,
        volume=last.volume,
    )

    assert generate_signal(make_too_short_candles()).action is SignalAction.NO_TRADE
    assert generate_signal(bad_candles).action is SignalAction.NO_TRADE


def test_strategy_returns_signal_objects_only() -> None:
    from conftest import make_bullish_pullback_candles

    signal = generate_signal(make_bullish_pullback_candles())

    assert isinstance(signal, Signal)
    assert not hasattr(signal, "broker")
    assert not hasattr(signal, "exchange")
    assert not hasattr(signal, "client")


def test_no_rsi_fields_config_imports_or_tests_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    checked_paths = [
        repo_root / "src" / "alpha_futures_bot",
        repo_root / "tests",
    ]

    for root in checked_paths:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            if path.name == "test_strategy.py":
                text = text.replace("rsi", "")
            assert "rsi" not in text
