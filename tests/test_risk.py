from __future__ import annotations

from dataclasses import fields

from alpha_futures_bot.config import BotConfig, RiskSettings
from alpha_futures_bot.models import Side, Signal, SignalAction, Symbol
from alpha_futures_bot.risk import evaluate_signal


def test_valid_long_signal_is_approved() -> None:
    from conftest import make_long_signal

    decision = evaluate_signal(make_long_signal(), account_balance=10_000.0)

    assert decision.approved is True
    assert decision.order is not None
    assert decision.order.side is Side.LONG


def test_valid_short_signal_is_approved() -> None:
    from conftest import make_short_signal

    decision = evaluate_signal(make_short_signal(), account_balance=10_000.0)

    assert decision.approved is True
    assert decision.order is not None
    assert decision.order.side is Side.SHORT


def test_decimal_risk_sizing_does_not_divide_by_100() -> None:
    from conftest import make_long_signal

    decision = evaluate_signal(make_long_signal(), account_balance=10_000.0)

    assert decision.order is not None
    assert decision.order.quantity == 10.0


def test_quantity_is_capped_by_max_notional() -> None:
    signal = Signal(
        symbol=Symbol.BTC,
        action=SignalAction.BUY,
        side=Side.LONG,
        score=80.0,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=110.0,
    )

    decision = evaluate_signal(signal, account_balance=100_000.0)

    assert decision.order is not None
    assert decision.order.quantity == 100.0


def test_no_trade_signal_is_rejected() -> None:
    signal = Signal(symbol=Symbol.BTC, action=SignalAction.NO_TRADE, score=0.0)

    decision = evaluate_signal(signal, account_balance=10_000.0)

    assert decision.approved is False


def test_low_score_is_rejected() -> None:
    from conftest import make_long_signal

    signal = make_long_signal()
    low_score = Signal(
        symbol=signal.symbol,
        action=signal.action,
        side=signal.side,
        score=69.0,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
    )

    assert evaluate_signal(low_score, account_balance=10_000.0).approved is False


def test_missing_entry_stop_or_take_profit_is_rejected() -> None:
    from conftest import make_long_signal

    signal = make_long_signal()
    missing_entry = Signal(
        symbol=signal.symbol,
        action=signal.action,
        side=signal.side,
        score=signal.score,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
    )
    missing_stop = Signal(
        symbol=signal.symbol,
        action=signal.action,
        side=signal.side,
        score=signal.score,
        entry_price=signal.entry_price,
        take_profit=signal.take_profit,
    )
    missing_profit = Signal(
        symbol=signal.symbol,
        action=signal.action,
        side=signal.side,
        score=signal.score,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
    )

    assert evaluate_signal(missing_entry, 10_000.0).approved is False
    assert evaluate_signal(missing_stop, 10_000.0).approved is False
    assert evaluate_signal(missing_profit, 10_000.0).approved is False


def test_wrong_side_stops_and_profits_are_rejected() -> None:
    bad_long_stop = Signal(Symbol.BTC, SignalAction.BUY, 80.0, side=Side.LONG, entry_price=100, stop_loss=101, take_profit=110)
    bad_long_profit = Signal(Symbol.BTC, SignalAction.BUY, 80.0, side=Side.LONG, entry_price=100, stop_loss=95, take_profit=99)
    bad_short_stop = Signal(Symbol.BTC, SignalAction.SELL, 80.0, side=Side.SHORT, entry_price=100, stop_loss=99, take_profit=90)
    bad_short_profit = Signal(Symbol.BTC, SignalAction.SELL, 80.0, side=Side.SHORT, entry_price=100, stop_loss=105, take_profit=101)

    assert evaluate_signal(bad_long_stop, 10_000.0).approved is False
    assert evaluate_signal(bad_long_profit, 10_000.0).approved is False
    assert evaluate_signal(bad_short_stop, 10_000.0).approved is False
    assert evaluate_signal(bad_short_profit, 10_000.0).approved is False


def test_unsupported_symbol_and_invalid_balance_are_rejected() -> None:
    signal = Signal("ETH", SignalAction.BUY, 80.0, side=Side.LONG, entry_price=100, stop_loss=95, take_profit=110)

    assert evaluate_signal(signal, 10_000.0).approved is False
    assert evaluate_signal(signal, 0.0).approved is False


def test_daily_loss_limit_is_rejected() -> None:
    from conftest import make_long_signal

    decision = evaluate_signal(make_long_signal(), account_balance=10_000.0, current_daily_loss=200.0)

    assert decision.approved is False


def test_no_exchange_or_private_key_fields_are_involved() -> None:
    forbidden_fragments = ("exchange", "api", "secret", "private", "key", "wallet")
    names = {field.name for field in fields(BotConfig)} | {field.name for field in fields(RiskSettings)}

    assert {name for name in names if any(fragment in name.lower() for fragment in forbidden_fragments)} == set()
