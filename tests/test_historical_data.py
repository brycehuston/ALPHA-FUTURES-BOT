from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from alpha_futures_bot.data import DataError, filter_candles_by_date_range, load_candles_from_csv, parse_backtest_date


def test_optional_historical_metadata_columns_are_accepted_and_ignored(tmp_path: Path) -> None:
    path = tmp_path / "historical.csv"
    path.write_text(
        "timestamp,symbol,open,high,low,close,volume,timeframe,source\n"
        "2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10,1h,manual\n",
        encoding="utf-8",
    )

    candles = load_candles_from_csv(path)

    assert len(candles) == 1
    assert candles[0].symbol.value == "BTC"
    assert candles[0].close == 100.0


def test_malformed_historical_row_fails_without_skipping(tmp_path: Path) -> None:
    path = tmp_path / "historical.csv"
    path.write_text(
        "timestamp,symbol,open,high,low,close,volume,timeframe\n"
        "2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10,1h\n"
        "bad-date,BTC,101,102,100,101,11,1h\n",
        encoding="utf-8",
    )

    with pytest.raises(DataError):
        load_candles_from_csv(path)


def test_large_local_historical_csv_loads_deterministically(tmp_path: Path) -> None:
    rows = [
        f"2024-01-{(index // 24) + 1:02d}T{index % 24:02d}:00:00+00:00,BTC,{100 + index},"
        f"{101 + index},{99 + index},{100 + index},10,1h"
        for index in range(500)
    ]
    path = tmp_path / "large.csv"
    path.write_text("timestamp,symbol,open,high,low,close,volume,timeframe\n" + "\n".join(rows) + "\n")

    candles = load_candles_from_csv(path)

    assert len(candles) == 500
    assert candles[0].close == 100.0
    assert candles[-1].close == 599.0


def test_parse_backtest_date_accepts_yyyy_mm_dd_only() -> None:
    assert parse_backtest_date("2024-01-31") == date(2024, 1, 31)
    assert parse_backtest_date(None) is None

    with pytest.raises(DataError):
        parse_backtest_date("2024-01-31T00:00:00")


def test_date_filter_start_only_end_only_and_inclusive_range(tmp_path: Path) -> None:
    candles = load_candles_from_csv(
        _write_csv(
            tmp_path,
            [
                "2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10",
                "2024-01-02T00:00:00+00:00,BTC,101,102,100,101,10",
                "2024-01-03T00:00:00+00:00,BTC,102,103,101,102,10",
            ],
        )
    )

    assert [c.close for c in filter_candles_by_date_range(candles, start=date(2024, 1, 2))] == [101.0, 102.0]
    assert [c.close for c in filter_candles_by_date_range(candles, end=date(2024, 1, 2))] == [100.0, 101.0]
    assert [
        c.close
        for c in filter_candles_by_date_range(candles, start=date(2024, 1, 2), end=date(2024, 1, 2))
    ] == [101.0]


def test_date_filter_rejects_invalid_ranges_and_empty_results(tmp_path: Path) -> None:
    candles = load_candles_from_csv(_write_csv(tmp_path, ["2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10"]))

    with pytest.raises(DataError):
        filter_candles_by_date_range(candles, start=date(2024, 1, 2), end=date(2024, 1, 1))
    with pytest.raises(DataError):
        filter_candles_by_date_range(candles, start=date(2024, 2, 1))


def _write_csv(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "candles.csv"
    path.write_text("timestamp,symbol,open,high,low,close,volume\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path
