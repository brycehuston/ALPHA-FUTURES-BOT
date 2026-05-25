"""Local CSV logging for offline paper simulations."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from alpha_futures_bot.models import ClosedPosition

SCAN_LOG_FIELDS = (
    "timestamp",
    "symbol",
    "close",
    "regime",
    "signal_action",
    "signal_side",
    "signal_score",
    "signal_reason",
    "position_accepted",
    "position_reason",
    "cash_balance",
    "realized_pnl",
    "unrealized_pnl",
    "open_position_side",
)

TRADE_LOG_FIELDS = (
    "closed_at",
    "symbol",
    "side",
    "quantity",
    "entry_price",
    "exit_price",
    "stop_loss",
    "take_profit",
    "realized_pnl",
    "close_reason",
    "cash_balance",
)


class LoggingError(ValueError):
    """Raised when local simulation logs cannot be written safely."""


class SimulationLogger:
    """CSV logger that writes local scan and trade rows only."""

    def __init__(self, logs_dir: str | Path = "logs") -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.scans_path = self.logs_dir / "scans.csv"
        self.trades_path = self.logs_dir / "trades.csv"
        self._ensure_file(self.scans_path, SCAN_LOG_FIELDS)
        self._ensure_file(self.trades_path, TRADE_LOG_FIELDS)
        self._trade_keys = self._load_trade_keys()

    def log_scan(self, row: Mapping[str, Any]) -> None:
        self._append_row(self.scans_path, SCAN_LOG_FIELDS, row)

    def log_trade(self, closed_position: ClosedPosition, cash_balance: float) -> bool:
        row = {
            "closed_at": closed_position.closed_at.isoformat(),
            "symbol": closed_position.symbol.value,
            "side": closed_position.side.value,
            "quantity": closed_position.quantity,
            "entry_price": closed_position.entry_price,
            "exit_price": closed_position.exit_price,
            "stop_loss": closed_position.stop_loss,
            "take_profit": closed_position.take_profit,
            "realized_pnl": closed_position.realized_pnl,
            "close_reason": closed_position.close_reason,
            "cash_balance": cash_balance,
        }
        trade_key = self._trade_key(row)
        if trade_key in self._trade_keys:
            return False
        self._append_row(self.trades_path, TRADE_LOG_FIELDS, row)
        self._trade_keys.add(trade_key)
        return True

    def _ensure_file(self, path: Path, fields: tuple[str, ...]) -> None:
        if path.exists():
            return
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()

    def _append_row(self, path: Path, fields: tuple[str, ...], row: Mapping[str, Any]) -> None:
        if set(row.keys()) != set(fields):
            raise LoggingError(f"Log row fields must match {path.name} schema")
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writerow({field: row[field] for field in fields})

    def _load_trade_keys(self) -> set[tuple[str, ...]]:
        keys: set[tuple[str, ...]] = set()
        with self.trades_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                keys.add(self._trade_key(row))
        return keys

    def _trade_key(self, row: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            str(row["closed_at"]),
            str(row["symbol"]),
            str(row["side"]),
            str(row["quantity"]),
            str(row["entry_price"]),
            str(row["exit_price"]),
            str(row["close_reason"]),
        )
