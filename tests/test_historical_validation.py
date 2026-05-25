from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_futures_bot.data import DataError
from alpha_futures_bot.historical_validation import validate_historical_csv


def test_valid_historical_csv_validation_passes(tmp_path: Path) -> None:
    path = _write_historical_csv(tmp_path, rows=_rows(200))

    report = validate_historical_csv(path)

    assert report.status == "PASS"
    assert report.file_name == "historical.csv"
    assert report.total_rows == 200
    assert report.valid_candle_count == 200
    assert report.filtered_candle_count == 200
    assert report.symbol == "BTC"
    assert report.enough_for_ema_200 is True
    assert report.detected_interval_seconds == 3600
    assert report.irregular_gap_count == 0
    assert report.warnings == ()


def test_optional_timeframe_and_source_columns_are_reported(tmp_path: Path) -> None:
    path = _write_historical_csv(
        tmp_path,
        header="timestamp,symbol,open,high,low,close,volume,timeframe,source,ignored_extra",
        rows=[f"{row},1h,manual,unused" for row in _rows(200)],
    )

    report = validate_historical_csv(path)

    assert report.status == "PASS"
    assert report.has_optional_timeframe_column is True
    assert report.timeframe_values_seen == ("1h",)
    assert report.has_optional_source_column is True
    assert report.source_values_seen == ("manual",)


def test_missing_required_columns_fail_with_column_names(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("timestamp,symbol,open,high,low\n2024-01-01T00:00:00+00:00,BTC,100,101,99\n")

    with pytest.raises(DataError, match="Missing required columns: close, volume"):
        validate_historical_csv(path)


def test_non_btc_rows_fail_with_row_number_and_symbol(tmp_path: Path) -> None:
    rows = _rows(200)
    rows[40] = rows[40].replace(",BTC,", ",ETH,")
    path = _write_historical_csv(tmp_path, rows=rows)

    with pytest.raises(DataError, match="Non-BTC symbol found at row 42: ETH"):
        validate_historical_csv(path)


def test_duplicate_timestamps_fail_with_timestamp(tmp_path: Path) -> None:
    rows = _rows(200)
    rows[10] = rows[9].replace(",109,", ",110,", 1)
    path = _write_historical_csv(tmp_path, rows=rows)

    with pytest.raises(DataError, match="Duplicate timestamp found: 2024-01-01T09:00:00\\+00:00"):
        validate_historical_csv(path)


def test_invalid_ohlcv_fails_with_specific_reason(tmp_path: Path) -> None:
    rows = _rows(200)
    rows[15] = "2024-01-01T15:00:00+00:00,BTC,115,114,113,115,10"
    path = _write_historical_csv(tmp_path, rows=rows)

    with pytest.raises(DataError, match="Invalid OHLCV at row 17: high is below open or close"):
        validate_historical_csv(path)


def test_malformed_timestamp_fails_with_row_number(tmp_path: Path) -> None:
    rows = _rows(200)
    rows[4] = "not-a-date,BTC,104,105,103,104,10"
    path = _write_historical_csv(tmp_path, rows=rows)

    with pytest.raises(DataError, match="Invalid timestamp at row 6"):
        validate_historical_csv(path)


def test_header_only_files_fail(tmp_path: Path) -> None:
    path = _write_historical_csv(tmp_path, rows=[])

    with pytest.raises(DataError, match="Empty CSV: no candle rows found"):
        validate_historical_csv(path)


def test_too_short_file_fails_as_not_backtest_ready(tmp_path: Path) -> None:
    path = _write_historical_csv(tmp_path, rows=_rows(199))

    with pytest.raises(DataError, match="Historical CSV has 199 candles after filtering"):
        validate_historical_csv(path)


def test_irregular_gaps_are_reported_as_warning(tmp_path: Path) -> None:
    rows = _rows(200, skip_after_index=100)
    path = _write_historical_csv(tmp_path, rows=rows)

    report = validate_historical_csv(path)

    assert report.status == "WARN"
    assert report.detected_interval_seconds is None
    assert report.irregular_gap_count == 1
    assert report.largest_gap_seconds == 7200
    assert report.warnings == ("Irregular candle gaps detected: 1",)


def test_unsorted_files_are_reported_deterministically(tmp_path: Path) -> None:
    rows = _rows(200)
    rows[0], rows[1] = rows[1], rows[0]
    path = _write_historical_csv(tmp_path, rows=rows)

    report = validate_historical_csv(path)

    assert report.status == "WARN"
    assert report.sorted_ascending is False
    assert report.filtered_first_timestamp == "2024-01-01T00:00:00+00:00"
    assert report.filtered_last_timestamp == "2024-01-09T07:00:00+00:00"
    assert report.warnings == ("Input rows are not sorted by ascending timestamp",)


def test_date_filtered_validation_reports_filtered_range(tmp_path: Path) -> None:
    path = _write_historical_csv(tmp_path, rows=_rows(240))

    report = validate_historical_csv(path, start=datetime(2024, 1, 2).date(), end=datetime(2024, 1, 10).date())

    assert report.status == "PASS"
    assert report.total_rows == 240
    assert report.filtered_candle_count == 216
    assert report.filtered_first_timestamp == "2024-01-02T00:00:00+00:00"
    assert report.filtered_last_timestamp == "2024-01-10T23:00:00+00:00"
    assert report.date_range_days == 9


def test_empty_filtered_range_fails(tmp_path: Path) -> None:
    path = _write_historical_csv(tmp_path, rows=_rows(240))

    with pytest.raises(DataError, match="Empty CSV after date filtering"):
        validate_historical_csv(path, start=datetime(2025, 1, 1).date())


def test_validation_module_has_no_network_or_exchange_behavior() -> None:
    source = Path("src/alpha_futures_bot/historical_validation.py").read_text(encoding="utf-8").lower()

    for forbidden in ("hyperliquid", "requests", "httpx", "urlopen", "socket", "api_key", "private_key"):
        assert forbidden not in source


def _rows(count: int, *, skip_after_index: int | None = None) -> list[str]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[str] = []
    for index in range(count):
        offset = index
        if skip_after_index is not None and index > skip_after_index:
            offset += 1
        timestamp = base + timedelta(hours=offset)
        open_price = 100 + index
        rows.append(
            ",".join(
                [
                    timestamp.isoformat(),
                    "BTC",
                    str(open_price),
                    str(open_price + 1),
                    str(open_price - 1),
                    str(open_price),
                    "10",
                ]
            )
        )
    return rows


def _write_historical_csv(
    tmp_path: Path,
    *,
    rows: list[str],
    header: str = "timestamp,symbol,open,high,low,close,volume",
) -> Path:
    path = tmp_path / "historical.csv"
    path.write_text(header + "\n" + "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return path
