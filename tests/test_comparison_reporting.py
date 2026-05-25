from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from alpha_futures_bot.logging_service import SimulationLogger
from alpha_futures_bot.reporting import build_backtest_report, build_comparison_report, build_comparison_row


def test_builds_comparison_report_rows_from_backtest_reports() -> None:
    report = build_backtest_report(
        total_candles=220,
        starting_balance=10_000.0,
        ending_balance=10_100.0,
        ending_equity=10_100.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[10_000.0, 10_100.0],
    )

    row = build_comparison_row(
        file_name="btc_2024.csv",
        start_date="2024-01-01",
        end_date="2024-12-31",
        report=report,
    )
    comparison = build_comparison_report([row])

    assert comparison.total_runs == 1
    assert comparison.rows[0].file_name == "btc_2024.csv"
    assert comparison.rows[0].start_date == "2024-01-01"
    assert comparison.rows[0].ending_equity == 10_100.0


def test_writes_valid_comparison_json_and_converts_non_finite_values(tmp_path: Path) -> None:
    report = build_backtest_report(
        total_candles=220,
        starting_balance=10_000.0,
        ending_balance=10_100.0,
        ending_equity=10_100.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[10_000.0, 10_100.0],
    )
    row = replace(build_comparison_row(file_name="btc.csv", start_date="", end_date="", report=report), profit_factor=float("inf"))
    logger = SimulationLogger(tmp_path / "logs", initialize_csv=False)

    logger.write_comparison(build_comparison_report([row]))

    payload = json.loads((tmp_path / "logs" / "comparison.json").read_text(encoding="utf-8"))
    assert payload["total_runs"] == 1
    assert payload["rows"][0]["profit_factor"] == "Infinity"


def test_comparison_json_has_no_secret_or_exchange_fields(tmp_path: Path) -> None:
    report = build_backtest_report(
        total_candles=0,
        starting_balance=10_000.0,
        ending_balance=10_000.0,
        ending_equity=10_000.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[],
    )
    logger = SimulationLogger(tmp_path / "logs", initialize_csv=False)

    logger.write_comparison(
        build_comparison_report([build_comparison_row(file_name="btc.csv", start_date="", end_date="", report=report)])
    )

    text = (tmp_path / "logs" / "comparison.json").read_text(encoding="utf-8").lower()
    for forbidden in ("api", "secret", "private", "key", "wallet", "exchange"):
        assert forbidden not in text
