"""Offline BTC paper simulation runner."""

from __future__ import annotations

import argparse
import re
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from alpha_futures_bot.broker import PaperBroker
from alpha_futures_bot.data import DataError, filter_candles_by_date_range, load_candles_from_csv, parse_backtest_date
from alpha_futures_bot.indicators import calculate_indicators
from alpha_futures_bot.logging_service import SimulationLogger
from alpha_futures_bot.models import Candle, Regime, Signal
from alpha_futures_bot.position import PositionDecision, PositionManager
from alpha_futures_bot.regime import detect_regime
from alpha_futures_bot.reporting import (
    BacktestComparisonReport,
    BacktestComparisonRow,
    BacktestReport,
    build_backtest_report,
    build_comparison_report,
    build_comparison_row,
)
from alpha_futures_bot.strategy import generate_signal


@dataclass(frozen=True, slots=True)
class SimulationSummary:
    source_file: str
    total_candles: int
    starting_balance: float
    ending_cash_balance: float
    realized_pnl: float
    open_position_count: int
    closed_trade_count: int
    scans_written: int
    report: BacktestReport


@dataclass(frozen=True, slots=True)
class MultiSimulationSummary:
    summaries: tuple[SimulationSummary, ...]
    comparison: BacktestComparisonReport


def run_simulation(
    candle_csv: str | Path,
    logs_dir: str | Path = "logs",
    starting_balance: float = 10_000.0,
    start: str | date | None = None,
    end: str | date | None = None,
    summary_name: str = "summary.json",
) -> SimulationSummary:
    start_date = parse_backtest_date(start) if isinstance(start, str) or start is None else start
    end_date = parse_backtest_date(end) if isinstance(end, str) or end is None else end
    candles = filter_candles_by_date_range(load_candles_from_csv(candle_csv), start_date, end_date)
    broker = PaperBroker(starting_balance=starting_balance)
    manager = PositionManager(broker)
    logger = SimulationLogger(logs_dir, summary_name=summary_name)
    scans_written = 0
    equity_curve: list[float] = []

    for index, candle in enumerate(candles):
        update = manager.update_from_candle(candle)
        if update.closed_position is not None:
            logger.log_trade(update.closed_position, broker.cash_balance)

        history = candles[: index + 1]
        signal = generate_signal(history)
        regime = detect_regime(calculate_indicators(history))
        decision = manager.handle_signal(signal, candle.timestamp)

        unrealized_pnl = broker.mark_to_market(candle.symbol, candle.close)
        equity_curve.append(broker.cash_balance + unrealized_pnl)
        open_position = broker.get_open_position(candle.symbol)
        logger.log_scan(
            _scan_row(
                candle=candle,
                regime=regime,
                signal=signal,
                decision=decision,
                cash_balance=broker.cash_balance,
                realized_pnl=broker.realized_pnl,
                unrealized_pnl=unrealized_pnl,
                open_position_side=open_position.side.value if open_position else "",
            )
        )
        scans_written += 1

    ending_equity = equity_curve[-1] if equity_curve else broker.cash_balance
    report = build_backtest_report(
        total_candles=len(candles),
        starting_balance=float(starting_balance),
        ending_balance=broker.cash_balance,
        ending_equity=ending_equity,
        open_position_count=len(broker.open_positions),
        closed_positions=broker.closed_positions,
        equity_curve=equity_curve,
    )
    logger.write_summary(report)

    return SimulationSummary(
        source_file=Path(candle_csv).name,
        total_candles=len(candles),
        starting_balance=float(starting_balance),
        ending_cash_balance=broker.cash_balance,
        realized_pnl=broker.realized_pnl,
        open_position_count=len(broker.open_positions),
        closed_trade_count=len(broker.closed_positions),
        scans_written=scans_written,
        report=report,
    )


def run_simulation_comparison(
    candle_csvs: Sequence[str | Path],
    logs_dir: str | Path = "logs",
    starting_balance: float = 10_000.0,
    start: str | date | None = None,
    end: str | date | None = None,
) -> MultiSimulationSummary:
    if len(candle_csvs) < 2:
        raise DataError("Comparison requires at least two local candle CSV files")

    root_logs_dir = Path(logs_dir)
    stems = _safe_run_stems(candle_csvs)
    summaries: list[SimulationSummary] = []
    rows: list[BacktestComparisonRow] = []
    start_label = _date_label(start)
    end_label = _date_label(end)

    for candle_csv, stem in zip(candle_csvs, stems):
        summary = run_simulation(
            candle_csv,
            root_logs_dir / "runs" / stem,
            starting_balance=starting_balance,
            start=start,
            end=end,
        )
        summaries.append(summary)
        rows.append(
            build_comparison_row(
                file_name=Path(candle_csv).name,
                start_date=start_label,
                end_date=end_label,
                report=summary.report,
            )
        )

    comparison = build_comparison_report(rows)
    SimulationLogger(root_logs_dir, initialize_csv=False).write_comparison(comparison)
    return MultiSimulationSummary(summaries=tuple(summaries), comparison=comparison)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run an offline BTC paper simulation.")
    parser.add_argument("--candles", nargs="+", required=True, help="One or more local BTC candle CSV paths.")
    parser.add_argument("--logs", default="logs", help="Directory for local scans.csv and trades.csv logs.")
    parser.add_argument("--start", help="Optional inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end", help="Optional inclusive end date in YYYY-MM-DD format.")
    parser.add_argument("--starting-balance", type=float, default=10_000.0)
    parser.add_argument("--summary-name", default="summary.json", help="Single-run summary JSON filename.")
    args = parser.parse_args(argv)

    if len(args.candles) == 1:
        summary = run_simulation(
            args.candles[0],
            args.logs,
            args.starting_balance,
            start=args.start,
            end=args.end,
            summary_name=args.summary_name,
        )
        print(_simulation_line(summary))
        return

    if args.summary_name != "summary.json":
        raise DataError("--summary-name is only supported for single-file runs")

    comparison = run_simulation_comparison(
        args.candles,
        args.logs,
        args.starting_balance,
        start=args.start,
        end=args.end,
    )
    print(f"Comparison complete: runs={comparison.comparison.total_runs}")
    for summary in comparison.summaries:
        print(_simulation_line(summary))


def _simulation_line(summary: SimulationSummary) -> str:
    return (
        "Simulation complete: "
        f"file={summary.source_file}, "
        f"candles={summary.total_candles}, "
        f"starting_balance={summary.starting_balance:.2f}, "
        f"ending_cash_balance={summary.ending_cash_balance:.2f}, "
        f"ending_equity={summary.report.ending_equity:.2f}, "
        f"realized_pnl={summary.realized_pnl:.2f}, "
        f"return_pct={summary.report.return_percentage:.2f}, "
        f"win_rate={summary.report.win_rate:.2f}, "
        f"profit_factor={_format_float(summary.report.profit_factor)}, "
        f"max_drawdown={summary.report.max_drawdown:.2f}, "
        f"open_positions={summary.open_position_count}, "
        f"closed_trades={summary.closed_trade_count}, "
        f"scans={summary.scans_written}"
    )


def _date_label(value: str | date | None) -> str:
    parsed = parse_backtest_date(value) if isinstance(value, str) or value is None else value
    return parsed.isoformat() if parsed else ""


def _safe_run_stems(candle_csvs: Sequence[str | Path]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    stems: list[str] = []
    for candle_csv in candle_csvs:
        base = Path(candle_csv).stem
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_").lower() or "candles"
        counts[safe] = counts.get(safe, 0) + 1
        if counts[safe] > 1:
            safe = f"{safe}_{counts[safe]}"
        stems.append(safe)
    return tuple(stems)


def _scan_row(
    *,
    candle: Candle,
    regime: Regime,
    signal: Signal,
    decision: PositionDecision,
    cash_balance: float,
    realized_pnl: float,
    unrealized_pnl: float,
    open_position_side: str,
) -> dict[str, object]:
    return {
        "timestamp": candle.timestamp.isoformat(),
        "symbol": candle.symbol.value,
        "close": candle.close,
        "regime": regime.value,
        "signal_action": signal.action.value,
        "signal_side": signal.side.value if signal.side else "",
        "signal_score": signal.score,
        "signal_reason": signal.reason,
        "position_accepted": decision.accepted,
        "position_reason": decision.reason,
        "cash_balance": cash_balance,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "open_position_side": open_position_side,
    }


def _format_float(value: float) -> str:
    if value == float("inf"):
        return "Infinity"
    if value == float("-inf"):
        return "-Infinity"
    return f"{value:.2f}"


if __name__ == "__main__":
    main()
