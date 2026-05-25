from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from alpha_futures_bot.logging_service import SimulationLogger
from alpha_futures_bot.reporting import build_backtest_report, build_preset_comparison_report, build_preset_comparison_row


def test_preset_comparison_report_builds_rows_and_rankings() -> None:
    strict = build_preset_comparison_row(
        preset_name="strict",
        report=_report(total_closed_trades=1, return_percentage=1.0, max_drawdown=10.0, profit_factor=1.5),
    )
    balanced = build_preset_comparison_row(
        preset_name="balanced",
        report=_report(total_closed_trades=2, return_percentage=2.0, max_drawdown=5.0, profit_factor=2.0),
    )
    loose = build_preset_comparison_row(
        preset_name="loose",
        report=_report(total_closed_trades=3, return_percentage=0.5, max_drawdown=20.0, profit_factor=1.0),
    )

    comparison = build_preset_comparison_report([strict, balanced, loose])

    assert comparison.total_presets == 3
    assert comparison.best_return_preset == "balanced"
    assert comparison.lowest_drawdown_preset == "balanced"
    assert comparison.best_profit_factor_preset == "balanced"
    assert comparison.most_trades_preset == "loose"
    assert comparison.fewest_trades_preset == "strict"


def test_writes_valid_preset_comparison_json_and_converts_infinity(tmp_path: Path) -> None:
    row = build_preset_comparison_row(preset_name="loose", report=_report())
    comparison = build_preset_comparison_report([replace(row, profit_factor=float("inf"))])
    logger = SimulationLogger(tmp_path / "logs", initialize_csv=False)

    logger.write_preset_comparison(comparison)

    payload = json.loads((tmp_path / "logs" / "preset_comparison.json").read_text(encoding="utf-8"))
    assert payload["total_presets"] == 1
    assert payload["rows"][0]["profit_factor"] == "Infinity"
    assert payload["best_return_preset"] == "loose"


def test_empty_preset_comparison_report_is_safe() -> None:
    comparison = build_preset_comparison_report([])

    assert comparison.total_presets == 0
    assert comparison.rows == ()
    assert comparison.best_return_preset == ""


def _report(
    *,
    total_closed_trades: int = 1,
    return_percentage: float = 1.0,
    max_drawdown: float = 0.0,
    profit_factor: float = 1.0,
):
    report = build_backtest_report(
        total_candles=220,
        starting_balance=10_000.0,
        ending_balance=10_100.0,
        ending_equity=10_100.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[10_000.0, 10_100.0],
    )
    return replace(
        report,
        total_closed_trades=total_closed_trades,
        realized_pnl=100.0,
        return_percentage=return_percentage,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        best_trade=100.0,
        worst_trade=-10.0,
        average_trade_pnl=50.0,
    )
