"""Basic paper position orchestration for Phase 3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from alpha_futures_bot.broker import BrokerError, PaperBroker
from alpha_futures_bot.config import BotConfig, default_config, validate_config
from alpha_futures_bot.models import Candle, ClosedPosition, PaperPosition, Signal, Symbol
from alpha_futures_bot.risk import evaluate_signal


@dataclass(frozen=True, slots=True)
class PositionDecision:
    accepted: bool
    reason: str
    position: PaperPosition | None = None


@dataclass(frozen=True, slots=True)
class PositionUpdate:
    closed: bool
    reason: str
    closed_position: ClosedPosition | None = None


class PositionManager:
    """Routes risk-approved signals to the local paper broker."""

    def __init__(self, broker: PaperBroker, config: BotConfig | None = None) -> None:
        self.broker = broker
        self.config = validate_config(config or default_config())

    def handle_signal(
        self,
        signal: Signal,
        timestamp: datetime,
        current_daily_loss: float = 0.0,
    ) -> PositionDecision:
        if len(self.broker.open_positions) >= self.config.risk.max_open_positions:
            return PositionDecision(False, "max open positions reached")
        if self.broker.get_open_position(Symbol.BTC) is not None:
            return PositionDecision(False, "duplicate BTC position")

        decision = evaluate_signal(
            signal,
            account_balance=self.broker.cash_balance,
            config=self.config,
            current_daily_loss=current_daily_loss,
        )
        if not decision.approved or decision.order is None:
            return PositionDecision(False, decision.reason)

        try:
            position = self.broker.submit_order(decision.order, timestamp)
        except BrokerError as exc:
            return PositionDecision(False, str(exc))
        return PositionDecision(True, "accepted", position)

    def update_from_candle(self, candle: Candle) -> PositionUpdate:
        if candle.symbol is not Symbol.BTC:
            return PositionUpdate(False, "invalid BTC candle")
        try:
            closed = self.broker.update_from_candle(candle)
        except BrokerError as exc:
            return PositionUpdate(False, str(exc))
        if closed is None:
            return PositionUpdate(False, "no position closed")
        return PositionUpdate(True, closed.close_reason, closed)
