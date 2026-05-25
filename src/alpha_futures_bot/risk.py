"""Fail-closed risk validation and sizing for paper orders."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from alpha_futures_bot.config import BotConfig, ConfigError, default_config, validate_config
from alpha_futures_bot.models import OrderRequest, Side, Signal, SignalAction, Symbol


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Result of validating a strategy signal for paper execution."""

    approved: bool
    reason: str
    order: OrderRequest | None = None


def evaluate_signal(
    signal: Signal,
    account_balance: float,
    config: BotConfig | None = None,
    current_daily_loss: float = 0.0,
) -> RiskDecision:
    """Validate a signal and size a local paper order."""

    try:
        config = validate_config(config or default_config())
    except ConfigError as exc:
        return _reject(f"invalid config: {exc}")

    if signal.symbol is not Symbol.BTC:
        return _reject("unsupported symbol")
    if signal.action is SignalAction.NO_TRADE:
        return _reject("no-trade signal")
    if signal.action is SignalAction.BUY and signal.side is not Side.LONG:
        return _reject("buy signal must be long")
    if signal.action is SignalAction.SELL and signal.side is not Side.SHORT:
        return _reject("sell signal must be short")
    if signal.score < config.risk.min_signal_score:
        return _reject("signal score below threshold")
    if not _positive_finite(account_balance):
        return _reject("invalid account balance")
    if not _finite_non_negative(current_daily_loss):
        return _reject("invalid current daily loss")
    if current_daily_loss >= account_balance * config.risk.daily_max_loss_pct:
        return _reject("daily loss limit reached")
    if not _positive_finite(signal.entry_price):
        return _reject("invalid entry price")
    if not _positive_finite(signal.stop_loss):
        return _reject("invalid stop loss")
    if not _positive_finite(signal.take_profit):
        return _reject("invalid take profit")

    entry_price = float(signal.entry_price)
    stop_loss = float(signal.stop_loss)
    take_profit = float(signal.take_profit)

    if signal.side is Side.LONG:
        if stop_loss >= entry_price:
            return _reject("long stop loss must be below entry")
        if take_profit <= entry_price:
            return _reject("long take profit must be above entry")
    elif signal.side is Side.SHORT:
        if stop_loss <= entry_price:
            return _reject("short stop loss must be above entry")
        if take_profit >= entry_price:
            return _reject("short take profit must be below entry")
    else:
        return _reject("missing side")

    stop_distance = abs(entry_price - stop_loss)
    if not _positive_finite(stop_distance):
        return _reject("invalid stop distance")

    risk_dollars = account_balance * config.risk.max_risk_per_trade_pct
    raw_quantity = risk_dollars / stop_distance
    notional_cap_quantity = config.risk.max_position_notional / entry_price
    quantity = min(raw_quantity, notional_cap_quantity)
    if not _positive_finite(quantity):
        return _reject("invalid quantity")

    return RiskDecision(
        approved=True,
        reason="approved",
        order=OrderRequest(
            symbol=Symbol.BTC,
            side=signal.side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        ),
    )


def _reject(reason: str) -> RiskDecision:
    return RiskDecision(approved=False, reason=reason)


def _positive_finite(value: float | None) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0


def _finite_non_negative(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0
