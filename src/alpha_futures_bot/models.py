"""Core typed models for the V1 paper/test-only bot skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BotMode(str, Enum):
    """Allowed V1 runtime modes."""

    PAPER = "PAPER"
    TEST = "TEST"


class Symbol(str, Enum):
    """Allowed V1 trading symbols."""

    BTC = "BTC"


class Side(str, Enum):
    """Position direction."""

    LONG = "LONG"
    SHORT = "SHORT"


class Regime(str, Enum):
    """Market regimes allowed by the V1 spec."""

    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    NO_TRADE = "NO_TRADE"


class SignalAction(str, Enum):
    """Strategy output action."""

    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True, slots=True)
class Candle:
    """Single OHLCV candle."""

    symbol: Symbol
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class Signal:
    """A proposed paper-trading signal before execution checks."""

    symbol: Symbol
    action: SignalAction
    score: float
    reason: str = ""
    side: Side | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """A simulated order request shape for future PaperBroker work."""

    symbol: Symbol
    side: Side
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float


@dataclass(frozen=True, slots=True)
class PaperPosition:
    """A simulated paper position shape for future position management."""

    symbol: Symbol
    side: Side
    quantity: float
    entry_price: float
    stop_loss: float
    opened_at: datetime
    take_profit: float


@dataclass(frozen=True, slots=True)
class ClosedPosition:
    """A completed simulated paper position."""

    symbol: Symbol
    side: Side
    quantity: float
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    opened_at: datetime
    closed_at: datetime
    realized_pnl: float
    close_reason: str
