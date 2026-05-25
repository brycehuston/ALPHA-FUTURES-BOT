"""Local broker interface and deterministic paper broker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from alpha_futures_bot.models import Candle, ClosedPosition, OrderRequest, PaperPosition, Side, Symbol


class BrokerError(ValueError):
    """Raised when a local paper broker operation is invalid."""


class BrokerBase(ABC):
    """Local broker interface for V1 paper execution only."""

    @abstractmethod
    def submit_order(self, order: OrderRequest, timestamp: datetime) -> PaperPosition:
        raise NotImplementedError

    @abstractmethod
    def close_position(
        self,
        symbol: Symbol,
        exit_price: float,
        timestamp: datetime,
        reason: str,
    ) -> ClosedPosition:
        raise NotImplementedError

    @abstractmethod
    def get_open_position(self, symbol: Symbol) -> PaperPosition | None:
        raise NotImplementedError

    @abstractmethod
    def update_from_candle(self, candle: Candle) -> ClosedPosition | None:
        raise NotImplementedError

    @abstractmethod
    def mark_to_market(self, symbol: Symbol, price: float) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def cash_balance(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def realized_pnl(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def open_positions(self) -> Mapping[Symbol, PaperPosition]:
        raise NotImplementedError

    @property
    @abstractmethod
    def closed_positions(self) -> tuple[ClosedPosition, ...]:
        raise NotImplementedError


class PaperBroker(BrokerBase):
    """In-memory paper broker with immediate deterministic fills."""

    def __init__(self, starting_balance: float = 10_000.0) -> None:
        if not _positive_finite(starting_balance):
            raise BrokerError("starting balance must be positive and finite")
        self._cash_balance = float(starting_balance)
        self._realized_pnl = 0.0
        self._open_positions: dict[Symbol, PaperPosition] = {}
        self._closed_positions: list[ClosedPosition] = []

    def submit_order(self, order: OrderRequest, timestamp: datetime) -> PaperPosition:
        _validate_order(order)
        if not isinstance(timestamp, datetime):
            raise BrokerError("timestamp must be a datetime")
        if order.symbol in self._open_positions:
            raise BrokerError("duplicate open position")
        position = PaperPosition(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=order.entry_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            opened_at=timestamp,
        )
        self._open_positions[order.symbol] = position
        return position

    def close_position(
        self,
        symbol: Symbol,
        exit_price: float,
        timestamp: datetime,
        reason: str,
    ) -> ClosedPosition:
        if symbol is not Symbol.BTC:
            raise BrokerError("unsupported symbol")
        if not _positive_finite(exit_price):
            raise BrokerError("exit price must be positive and finite")
        if not isinstance(timestamp, datetime):
            raise BrokerError("timestamp must be a datetime")
        position = self._open_positions.pop(symbol, None)
        if position is None:
            raise BrokerError("no open position")

        realized_pnl = _position_pnl(position, exit_price)
        self._realized_pnl += realized_pnl
        self._cash_balance += realized_pnl
        closed = ClosedPosition(
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=float(exit_price),
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            opened_at=position.opened_at,
            closed_at=timestamp,
            realized_pnl=realized_pnl,
            close_reason=reason,
        )
        self._closed_positions.append(closed)
        return closed

    def get_open_position(self, symbol: Symbol) -> PaperPosition | None:
        if symbol is not Symbol.BTC:
            return None
        return self._open_positions.get(symbol)

    def update_from_candle(self, candle: Candle) -> ClosedPosition | None:
        if candle.symbol is not Symbol.BTC or not _valid_candle(candle):
            raise BrokerError("invalid BTC candle")
        position = self.get_open_position(Symbol.BTC)
        if position is None:
            return None

        if position.side is Side.LONG:
            if candle.low <= position.stop_loss:
                return self.close_position(position.symbol, position.stop_loss, candle.timestamp, "stop_loss")
            if candle.high >= position.take_profit:
                return self.close_position(position.symbol, position.take_profit, candle.timestamp, "take_profit")
        if position.side is Side.SHORT:
            if candle.high >= position.stop_loss:
                return self.close_position(position.symbol, position.stop_loss, candle.timestamp, "stop_loss")
            if candle.low <= position.take_profit:
                return self.close_position(position.symbol, position.take_profit, candle.timestamp, "take_profit")
        return None

    def mark_to_market(self, symbol: Symbol, price: float) -> float:
        if symbol is not Symbol.BTC:
            raise BrokerError("unsupported symbol")
        if not _positive_finite(price):
            raise BrokerError("price must be positive and finite")
        position = self.get_open_position(symbol)
        if position is None:
            return 0.0
        return _position_pnl(position, float(price))

    @property
    def cash_balance(self) -> float:
        return self._cash_balance

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def open_positions(self) -> Mapping[Symbol, PaperPosition]:
        return MappingProxyType(self._open_positions)

    @property
    def closed_positions(self) -> tuple[ClosedPosition, ...]:
        return tuple(self._closed_positions)


def _validate_order(order: OrderRequest) -> None:
    if order.symbol is not Symbol.BTC:
        raise BrokerError("unsupported symbol")
    if order.side not in {Side.LONG, Side.SHORT}:
        raise BrokerError("unsupported side")
    for name in ("quantity", "entry_price", "stop_loss", "take_profit"):
        if not _positive_finite(getattr(order, name)):
            raise BrokerError(f"{name} must be positive and finite")
    if order.side is Side.LONG:
        if order.stop_loss >= order.entry_price:
            raise BrokerError("long stop loss must be below entry")
        if order.take_profit <= order.entry_price:
            raise BrokerError("long take profit must be above entry")
    if order.side is Side.SHORT:
        if order.stop_loss <= order.entry_price:
            raise BrokerError("short stop loss must be above entry")
        if order.take_profit >= order.entry_price:
            raise BrokerError("short take profit must be below entry")


def _position_pnl(position: PaperPosition, exit_price: float) -> float:
    if position.side is Side.LONG:
        return (float(exit_price) - position.entry_price) * position.quantity
    return (position.entry_price - float(exit_price)) * position.quantity


def _valid_candle(candle: Candle) -> bool:
    values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) for value in values):
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


def _positive_finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0
