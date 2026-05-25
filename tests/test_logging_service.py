from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from alpha_futures_bot.logging_service import SCAN_LOG_FIELDS, TRADE_LOG_FIELDS, SimulationLogger
from alpha_futures_bot.models import ClosedPosition, Side, Symbol


def test_creates_logs_directory_and_default_headers(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"

    SimulationLogger(logs_dir)

    assert (logs_dir / "scans.csv").exists()
    assert (logs_dir / "trades.csv").exists()
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
