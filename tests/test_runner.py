from __future__ import annotations

import csv
import json
from pathlib import Path

from alpha_futures_bot.runner import SimulationSummary, run_simulation


def test_full_offline_simulation_writes_logs_and_summary(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    summary = run_simulation(csv_path, logs_dir)

    assert isinstance(summary, SimulationSummary)
    assert summary.total_candles == 221
    assert summary.scans_written == 221
    assert summary.report.total_candles == 221
    assert summary.report.total_closed_trades >= 1
    assert summary.report.ending_equity >= summary.report.ending_balance
    assert (logs_dir / "scans.csv").exists()
    assert (logs_dir / "trades.csv").exists()
    assert (logs_dir / "summary.json").exists()
    assert len(_rows(logs_dir / "scans.csv")) == 221
    assert len(_rows(logs_dir / "trades.csv")) >= 1
    payload = json.loads((logs_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["total_candles"] == 221
    assert "profit_factor" in payload


def test_runner_handles_short_history_without_crashing(tmp_path: Path) -> None:
    csv_path = tmp_path / "short.csv"
    csv_path.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-01-01T00:00:00+00:00,BTC,100,101,99,100,10\n"
        "2026-01-01T00:01:00+00:00,BTC,101,102,100,101,10\n"
    )

    summary = run_simulation(csv_path, tmp_path / "logs")

    assert summary.total_candles == 2
    assert summary.scans_written == 2
    assert summary.closed_trade_count == 0
    assert summary.report.total_closed_trades == 0
    assert summary.report.win_rate == 0.0
    payload = json.loads((tmp_path / "logs" / "summary.json").read_text(encoding="utf-8"))
    assert payload["total_closed_trades"] == 0


def test_runner_uses_position_manager_decision_not_direct_risk_call() -> None:
    source = Path("src/alpha_futures_bot/runner.py").read_text(encoding="utf-8")

    assert "handle_signal(" in source
    assert "evaluate_signal" not in source
    assert "alpha_futures_bot.risk" not in source


def test_runner_uses_paper_broker_only_and_no_network_or_exchange_modules() -> None:
    source = Path("src/alpha_futures_bot/runner.py").read_text(encoding="utf-8").lower()

    assert "paperbroker" in source
    for forbidden in ("hyperliquid", "requests", "httpx", "urlopen", "socket", "api_key", "private_key"):
        assert forbidden not in source


def _write_trade_simulation_csv(tmp_path: Path) -> Path:
    from conftest import make_bullish_pullback_candles
    from alpha_futures_bot.models import Candle, Symbol
    from alpha_futures_bot.strategy import generate_signal

    candles = make_bullish_pullback_candles()
    signal = generate_signal(candles)
    assert signal.take_profit is not None
    last = candles[-1]
    candles.append(
        Candle(
            symbol=Symbol.BTC,
            timestamp=last.timestamp.replace(minute=last.timestamp.minute + 1),
            open=last.close,
            high=signal.take_profit + 1.0,
            low=last.close,
            close=signal.take_profit,
            volume=150.0,
        )
    )
    path = tmp_path / "simulation.csv"
    lines = ["timestamp,symbol,open,high,low,close,volume"]
    for candle in candles:
        lines.append(
            ",".join(
                [
                    candle.timestamp.isoformat(),
                    candle.symbol.value,
                    str(candle.open),
                    str(candle.high),
                    str(candle.low),
                    str(candle.close),
                    str(candle.volume),
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n")
    return path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
