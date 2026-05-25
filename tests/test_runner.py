from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_futures_bot.data import DataError
from alpha_futures_bot.presets import LOOSE_PRESET, PresetError
from alpha_futures_bot.runner import SimulationSummary, run_simulation
from alpha_futures_bot.runner import main as runner_main
from alpha_futures_bot.runner import _config_for_preset, run_preset_comparison, run_simulation_comparison


def test_full_offline_simulation_writes_logs_and_summary(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    summary = run_simulation(csv_path, logs_dir)

    assert isinstance(summary, SimulationSummary)
    assert summary.total_candles == 221
    assert summary.preset_name == "balanced"
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


def test_balanced_preset_preserves_default_runner_behavior(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    default_summary = run_simulation(csv_path, tmp_path / "default")
    balanced_summary = run_simulation(csv_path, tmp_path / "balanced", preset="balanced")

    assert balanced_summary.report == default_summary.report
    assert balanced_summary.preset_name == "balanced"


def test_loose_preset_uses_derived_risk_config_with_min_score_60() -> None:
    config = _config_for_preset(LOOSE_PRESET)

    assert config.risk.min_signal_score == 60.0
    assert config.risk.max_risk_per_trade_pct == 0.005
    assert config.risk.max_position_notional == 10_000.0


def test_invalid_preset_fails_closed(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    with pytest.raises(PresetError):
        run_simulation(csv_path, tmp_path / "logs", preset="remote")


def test_single_run_can_write_sanitized_custom_summary_name(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    run_simulation(csv_path, logs_dir, summary_name="custom_summary.json")

    assert (logs_dir / "custom_summary.json").exists()
    assert not (logs_dir / "summary.json").exists()


def test_single_run_rejects_unsafe_summary_names(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    for unsafe in ("../summary.json", r"..\summary.json", "nested/summary.json", "summary.txt"):
        with pytest.raises(ValueError):
            run_simulation(csv_path, tmp_path / "logs", summary_name=unsafe)


def test_filtered_run_reports_reduced_candle_count(tmp_path: Path) -> None:
    csv_path = tmp_path / "dates.csv"
    csv_path.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10\n"
        "2024-01-02T00:00:00+00:00,BTC,101,102,100,101,10\n"
        "2024-01-03T00:00:00+00:00,BTC,102,103,101,102,10\n",
        encoding="utf-8",
    )

    summary = run_simulation(csv_path, tmp_path / "logs", start="2024-01-02", end="2024-01-03")

    assert summary.total_candles == 2
    assert summary.scans_written == 2


def test_filtered_run_rejects_empty_date_range(tmp_path: Path) -> None:
    csv_path = tmp_path / "dates.csv"
    csv_path.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10\n",
        encoding="utf-8",
    )

    with pytest.raises(DataError):
        run_simulation(csv_path, tmp_path / "logs", start="2025-01-01")


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


def test_multi_file_comparison_runs_independently_and_writes_isolated_logs(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    summary = run_simulation_comparison([csv_path, csv_path], logs_dir)

    assert summary.comparison.total_runs == 2
    assert len(summary.summaries) == 2
    assert (logs_dir / "comparison.json").exists()
    assert (logs_dir / "runs" / "simulation" / "scans.csv").exists()
    assert (logs_dir / "runs" / "simulation" / "trades.csv").exists()
    assert (logs_dir / "runs" / "simulation" / "summary.json").exists()
    assert (logs_dir / "runs" / "simulation_2" / "summary.json").exists()
    assert not (logs_dir / "scans.csv").exists()
    assert not (logs_dir / "trades.csv").exists()
    payload = json.loads((logs_dir / "comparison.json").read_text(encoding="utf-8"))
    assert payload["total_runs"] == 2
    assert payload["rows"][0]["file_name"] == "simulation.csv"


def test_preset_comparison_runs_all_presets_and_writes_isolated_logs(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    summary = run_preset_comparison(csv_path, logs_dir)

    assert summary.comparison.total_presets == 3
    assert [item.preset_name for item in summary.summaries] == ["strict", "balanced", "loose"]
    assert (logs_dir / "preset_comparison.json").exists()
    for preset_name in ("strict", "balanced", "loose"):
        assert (logs_dir / "presets" / preset_name / "scans.csv").exists()
        assert (logs_dir / "presets" / preset_name / "trades.csv").exists()
        assert (logs_dir / "presets" / preset_name / "summary.json").exists()
    payload = json.loads((logs_dir / "preset_comparison.json").read_text(encoding="utf-8"))
    assert payload["total_presets"] == 3


def test_cli_compare_presets_rejects_multiple_candle_files(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    with pytest.raises(DataError):
        runner_main(["--candles", str(csv_path), str(csv_path), "--logs", str(tmp_path / "logs"), "--compare-presets"])


def test_cli_compare_presets_rejects_custom_summary_name(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    with pytest.raises(DataError):
        runner_main(
            [
                "--candles",
                str(csv_path),
                "--logs",
                str(tmp_path / "logs"),
                "--compare-presets",
                "--summary-name",
                "custom.json",
            ]
        )


def test_cli_rejects_summary_name_for_multi_file_run(tmp_path: Path) -> None:
    csv_path = _write_trade_simulation_csv(tmp_path)

    with pytest.raises(DataError):
        runner_main(
            [
                "--candles",
                str(csv_path),
                str(csv_path),
                "--logs",
                str(tmp_path / "logs"),
                "--summary-name",
                "custom.json",
            ]
        )


def test_cli_validate_csv_prints_summary_without_writing_logs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = _write_validation_ready_csv(tmp_path)
    logs_dir = tmp_path / "logs"

    runner_main(["--validate-csv", str(csv_path), "--logs", str(logs_dir)])

    output = capsys.readouterr().out
    assert "CSV validation PASS: file=validation.csv" in output
    assert "filtered_candle_count=200" in output
    assert not logs_dir.exists()


def test_cli_validate_csv_accepts_start_and_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = _write_validation_ready_csv(tmp_path, count=240)

    runner_main(
        [
            "--validate-csv",
            str(csv_path),
            "--start",
            "2024-01-02",
            "--end",
            "2024-01-10",
        ]
    )

    output = capsys.readouterr().out
    assert "CSV validation PASS: file=validation.csv" in output
    assert "filtered_candle_count=216" in output
    assert "filtered_first_timestamp=2024-01-02T00:00:00+00:00" in output
    assert "filtered_last_timestamp=2024-01-10T23:00:00+00:00" in output


def test_cli_validate_csv_rejects_candles_combo(tmp_path: Path) -> None:
    csv_path = _write_validation_ready_csv(tmp_path)

    with pytest.raises(DataError, match="--validate-csv cannot be combined with --candles"):
        runner_main(["--validate-csv", str(csv_path), "--candles", str(csv_path)])


def test_cli_validate_csv_rejects_compare_presets_combo(tmp_path: Path) -> None:
    csv_path = _write_validation_ready_csv(tmp_path)

    with pytest.raises(DataError, match="--validate-csv cannot be combined with --compare-presets"):
        runner_main(["--validate-csv", str(csv_path), "--compare-presets"])


def test_cli_requires_candles_without_validation_mode() -> None:
    with pytest.raises(DataError, match="--candles is required unless --validate-csv is used"):
        runner_main([])


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


def _write_validation_ready_csv(tmp_path: Path, *, count: int = 200) -> Path:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    lines = ["timestamp,symbol,open,high,low,close,volume"]
    for index in range(count):
        timestamp = base + timedelta(hours=index)
        price = 100 + index
        lines.append(
            ",".join(
                [
                    timestamp.isoformat(),
                    "BTC",
                    str(price),
                    str(price + 1),
                    str(price - 1),
                    str(price),
                    "10",
                ]
            )
        )
    path = tmp_path / "validation.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
