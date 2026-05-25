"""Local deterministic backtest-style reporting for paper simulations."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite
from typing import Sequence

from alpha_futures_bot.models import ClosedPosition


@dataclass(frozen=True, slots=True)
class BacktestReport:
    total_candles: int
    total_closed_trades: int
    open_position_count: int
    starting_balance: float
    ending_balance: float
    ending_equity: float
    realized_pnl: float
    return_percentage: float
    win_count: int
    loss_count: int
    win_rate: float
    average_win: float
    average_loss: float
    best_trade: float
    worst_trade: float
    profit_factor: float
    max_drawdown: float
    equity_high: float
    equity_low: float
    average_trade_pnl: float


def build_backtest_report(
    *,
    total_candles: int,
    starting_balance: float,
    ending_balance: float,
    ending_equity: float,
    open_position_count: int,
    closed_positions: Sequence[ClosedPosition],
    equity_curve: Sequence[float],
) -> BacktestReport:
    """Build deterministic local reporting metrics from paper-broker state."""

    trade_pnls = [position.realized_pnl for position in closed_positions]
    wins = [pnl for pnl in trade_pnls if pnl > 0]
    losses = [pnl for pnl in trade_pnls if pnl < 0]
    total_closed_trades = len(trade_pnls)
    realized_pnl = sum(trade_pnls)
    safe_equity_curve = _safe_equity_curve(equity_curve, starting_balance)
    equity_high = max(safe_equity_curve)
    equity_low = min(safe_equity_curve)
    return_percentage = 0.0
    if _positive_finite(starting_balance):
        return_percentage = ((ending_equity - starting_balance) / starting_balance) * 100.0

    return BacktestReport(
        total_candles=total_candles,
        total_closed_trades=total_closed_trades,
        open_position_count=open_position_count,
        starting_balance=float(starting_balance),
        ending_balance=float(ending_balance),
        ending_equity=float(ending_equity),
        realized_pnl=realized_pnl,
        return_percentage=return_percentage,
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=(len(wins) / total_closed_trades * 100.0) if total_closed_trades else 0.0,
        average_win=(sum(wins) / len(wins)) if wins else 0.0,
        average_loss=(sum(losses) / len(losses)) if losses else 0.0,
        best_trade=max(trade_pnls) if trade_pnls else 0.0,
        worst_trade=min(trade_pnls) if trade_pnls else 0.0,
        profit_factor=_profit_factor(wins, losses),
        max_drawdown=_max_drawdown(safe_equity_curve),
        equity_high=equity_high,
        equity_low=equity_low,
        average_trade_pnl=(realized_pnl / total_closed_trades) if total_closed_trades else 0.0,
    )


def _profit_factor(wins: Sequence[float], losses: Sequence[float]) -> float:
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    if gross_losses > 0:
        return gross_wins / gross_losses
    if gross_wins > 0:
        return inf
    return 0.0


def _max_drawdown(equity_curve: Sequence[float]) -> float:
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return max_drawdown


def _safe_equity_curve(equity_curve: Sequence[float], starting_balance: float) -> list[float]:
    finite_values = [float(value) for value in equity_curve if isinstance(value, (int, float)) and isfinite(value)]
    if finite_values:
        return finite_values
    return [float(starting_balance) if isfinite(starting_balance) else 0.0]


def _positive_finite(value: float) -> bool:
    return isinstance(value, (int, float)) and isfinite(value) and value > 0
