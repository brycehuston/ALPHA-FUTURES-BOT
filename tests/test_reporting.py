from __future__ import annotations

from datetime import datetime, timezone

from alpha_futures_bot.models import ClosedPosition, Side, Symbol
from alpha_futures_bot.reporting import build_backtest_report


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_report_metrics_with_wins_and_losses() -> None:
    trades = [_closed_position(100.0), _closed_position(-50.0), _closed_position(25.0)]

    report = build_backtest_report(
        total_candles=10,
        starting_balance=1_000.0,
        ending_balance=1_075.0,
        ending_equity=1_075.0,
        open_position_count=0,
        closed_positions=trades,
        equity_curve=[1_000.0, 1_100.0, 1_050.0, 1_075.0],
    )

    assert report.total_candles == 10
    assert report.total_closed_trades == 3
    assert report.win_count == 2
    assert report.loss_count == 1
    assert report.win_rate == 2 / 3 * 100
    assert report.average_win == 62.5
    assert report.average_loss == -50.0
    assert report.best_trade == 100.0
    assert report.worst_trade == -50.0
    assert report.average_trade_pnl == 25.0
    assert report.return_percentage == 7.5
    assert report.profit_factor == 2.5


def test_zero_trade_report_is_safe() -> None:
    report = build_backtest_report(
        total_candles=2,
        starting_balance=1_000.0,
        ending_balance=1_000.0,
        ending_equity=1_000.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[],
    )

    assert report.total_closed_trades == 0
    assert report.win_count == 0
    assert report.loss_count == 0
    assert report.win_rate == 0.0
    assert report.average_win == 0.0
    assert report.average_loss == 0.0
    assert report.best_trade == 0.0
    assert report.worst_trade == 0.0
    assert report.profit_factor == 0.0
    assert report.average_trade_pnl == 0.0
    assert report.max_drawdown == 0.0


def test_profit_factor_is_infinite_with_wins_and_no_losses() -> None:
    report = build_backtest_report(
        total_candles=5,
        starting_balance=1_000.0,
        ending_balance=1_100.0,
        ending_equity=1_100.0,
        open_position_count=0,
        closed_positions=[_closed_position(100.0)],
        equity_curve=[1_000.0, 1_100.0],
    )

    assert report.profit_factor == float("inf")


def test_max_drawdown_equity_high_and_equity_low() -> None:
    report = build_backtest_report(
        total_candles=5,
        starting_balance=1_000.0,
        ending_balance=1_060.0,
        ending_equity=1_060.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[1_000.0, 1_200.0, 1_050.0, 1_100.0, 1_060.0],
    )

    assert report.equity_high == 1_200.0
    assert report.equity_low == 1_000.0
    assert report.max_drawdown == 150.0


def test_ending_equity_can_differ_from_ending_balance() -> None:
    report = build_backtest_report(
        total_candles=5,
        starting_balance=1_000.0,
        ending_balance=1_000.0,
        ending_equity=1_050.0,
        open_position_count=1,
        closed_positions=[],
        equity_curve=[1_000.0, 1_050.0],
    )

    assert report.ending_balance == 1_000.0
    assert report.ending_equity == 1_050.0
    assert report.return_percentage == 5.0


def _closed_position(realized_pnl: float) -> ClosedPosition:
    return ClosedPosition(
        symbol=Symbol.BTC,
        side=Side.LONG,
        quantity=1.0,
        entry_price=100.0,
        exit_price=100.0 + realized_pnl,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=NOW,
        closed_at=NOW,
        realized_pnl=realized_pnl,
        close_reason="test",
    )
