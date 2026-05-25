from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from alpha_futures_bot.logging_service import LoggingError, SCAN_LOG_FIELDS, TRADE_LOG_FIELDS, SimulationLogger
from alpha_futures_bot.models import ClosedPosition, Side, Symbol
from alpha_futures_bot.reporting import build_backtest_report


def test_creates_logs_directory_and_default_headers(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"

    logger = SimulationLogger(logs_dir)

    assert (logs_dir / "scans.csv").exists()
    assert (logs_dir / "trades.csv").exists()
    assert logger.summary_path == logs_dir / "summary.json"
    assert _header(logs_dir / "scans.csv") == list(SCAN_LOG_FIELDS)
    assert _header(logs_dir / "trades.csv") == list(TRADE_LOG_FIELDS)
    assert not (logs_dir / "scan_log.csv").exists()
    assert not (logs_dir / "trade_log.csv").exists()


def test_appends_scan_rows(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs")

    logger.log_scan(_scan_row())

    rows = _rows(logger.scans_path)
    assert len(rows) == 1
    assert rows[0]["position_accepted"] == "False"


def test_appends_trade_rows_and_prevents_duplicates(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs")
    closed = _closed_position()

    assert logger.log_trade(closed, cash_balance=10_010.0) is True
    assert logger.log_trade(closed, cash_balance=10_010.0) is False

    rows = _rows(logger.trades_path)
    assert len(rows) == 1
    assert rows[0]["close_reason"] == "take_profit"


def test_existing_trade_rows_are_loaded_for_duplicate_prevention(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    first = SimulationLogger(logs_dir)
    closed = _closed_position()
    assert first.log_trade(closed, cash_balance=10_010.0) is True

    second = SimulationLogger(logs_dir)
    assert second.log_trade(closed, cash_balance=10_010.0) is False


def test_headers_do_not_include_secret_or_exchange_fields(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs")
    forbidden = ("api", "secret", "private", "key", "wallet", "exchange")

    headers = _header(logger.scans_path) + _header(logger.trades_path)

    assert not [field for field in headers if any(fragment in field for fragment in forbidden)]


def test_writes_valid_summary_json_and_converts_infinity(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs")
    report = build_backtest_report(
        total_candles=5,
        starting_balance=1_000.0,
        ending_balance=1_100.0,
        ending_equity=1_100.0,
        open_position_count=0,
        closed_positions=[_closed_position()],
        equity_curve=[1_000.0, 1_100.0],
    )

    logger.write_summary(report)

    payload = json.loads(logger.summary_path.read_text(encoding="utf-8"))
    assert payload["profit_factor"] == "Infinity"
    assert payload["ending_equity"] == 1_100.0


def test_custom_summary_name_must_be_safe_local_json_filename(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs", summary_name="safe_summary.json")

    assert logger.summary_path == tmp_path / "logs" / "safe_summary.json"

    for unsafe in ("../summary.json", r"..\summary.json", "nested/summary.json", "C:/tmp/summary.json", "summary.txt", ""):
        with pytest.raises(LoggingError):
            SimulationLogger(tmp_path / "logs", summary_name=unsafe)


def test_write_comparison_does_not_require_root_scan_trade_logs(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logger = SimulationLogger(logs_dir, initialize_csv=False)
    report = build_backtest_report(
        total_candles=0,
        starting_balance=1_000.0,
        ending_balance=1_000.0,
        ending_equity=1_000.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[],
    )

    logger.write_comparison({"total_runs": 1, "rows": [{"file_name": "btc.csv", "profit_factor": report.profit_factor}]})

    assert (logs_dir / "comparison.json").exists()
    assert not (logs_dir / "scans.csv").exists()
    assert not (logs_dir / "trades.csv").exists()


def test_summary_json_has_no_secret_or_exchange_fields(tmp_path: Path) -> None:
    logger = SimulationLogger(tmp_path / "logs")
    report = build_backtest_report(
        total_candles=0,
        starting_balance=1_000.0,
        ending_balance=1_000.0,
        ending_equity=1_000.0,
        open_position_count=0,
        closed_positions=[],
        equity_curve=[],
    )

    logger.write_summary(report)

    text = logger.summary_path.read_text(encoding="utf-8").lower()
    for forbidden in ("api", "secret", "private", "key", "wallet", "exchange"):
        assert forbidden not in text


def _scan_row() -> dict[str, object]:
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "symbol": "BTC",
        "close": 100.0,
        "regime": "NO_TRADE",
        "signal_action": "NO_TRADE",
        "signal_side": "",
        "signal_score": 0.0,
        "signal_reason": "test",
        "position_accepted": False,
        "position_reason": "no-trade signal",
        "cash_balance": 10_000.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "open_position_side": "",
    }


def _closed_position() -> ClosedPosition:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return ClosedPosition(
        symbol=Symbol.BTC,
        side=Side.LONG,
        quantity=1.0,
        entry_price=100.0,
        exit_price=110.0,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=now,
        closed_at=now,
        realized_pnl=10.0,
        close_reason="take_profit",
    )


def _header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
