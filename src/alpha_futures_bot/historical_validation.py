"""Offline sanity checks for user-provided BTC historical CSV files."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from alpha_futures_bot.data import DataError, REQUIRED_CANDLE_COLUMNS, parse_candle_row
from alpha_futures_bot.models import Candle

EMA_200_MIN_CANDLES = 200
OPTIONAL_HISTORICAL_COLUMNS = ("timeframe", "source")


@dataclass(frozen=True, slots=True)
class HistoricalDataReport:
    file_name: str
    total_rows: int
    valid_candle_count: int
    filtered_candle_count: int
    first_timestamp: str
    last_timestamp: str
    filtered_first_timestamp: str
    filtered_last_timestamp: str
    date_range_days: int
    symbol: str
    has_optional_timeframe_column: bool
    timeframe_values_seen: tuple[str, ...]
    has_optional_source_column: bool
    source_values_seen: tuple[str, ...]
    duplicate_timestamp_count: int
    sorted_ascending: bool
    minimum_close: float
    maximum_close: float
    minimum_volume: float
    maximum_volume: float
    enough_for_ema_200: bool
    detected_interval_seconds: int | None
    irregular_gap_count: int
    largest_gap_seconds: int | None
    status: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


def validate_historical_csv(
    path: str | Path,
    start: date | None = None,
    end: date | None = None,
) -> HistoricalDataReport:
    """Validate one local BTC historical CSV and return a deterministic sanity report."""

    if start is not None and end is not None and start > end:
        raise DataError("Backtest start date must be before or equal to end date")

    csv_path = Path(path)
    if not csv_path.is_file():
        raise DataError(f"Candle CSV does not exist: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataError("Candle CSV is missing a header row")
        missing_columns = set(REQUIRED_CANDLE_COLUMNS) - set(reader.fieldnames)
        if missing_columns:
            raise DataError(f"Missing required columns: {_format_missing_columns(missing_columns)}")

        candles: list[Candle] = []
        input_timestamps: list[datetime] = []
        seen_timestamps: set[datetime] = set()
        timeframe_values: set[str] = set()
        source_values: set[str] = set()
        has_timeframe = "timeframe" in reader.fieldnames
        has_source = "source" in reader.fieldnames

        for row_number, row in enumerate(reader, start=2):
            candle = parse_candle_row(row, row_number)
            if candle.timestamp in seen_timestamps:
                raise DataError(f"Duplicate timestamp found: {candle.timestamp.isoformat()}")
            seen_timestamps.add(candle.timestamp)
            input_timestamps.append(candle.timestamp)
            candles.append(candle)
            if has_timeframe:
                value = (row.get("timeframe") or "").strip()
                if value:
                    timeframe_values.add(value)
            if has_source:
                value = (row.get("source") or "").strip()
                if value:
                    source_values.add(value)

    if not candles:
        raise DataError("Empty CSV: no candle rows found")

    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    filtered_candles = _filter_candles(sorted_candles, start, end)
    if not filtered_candles:
        raise DataError("Empty CSV after date filtering")

    enough_for_ema_200 = len(filtered_candles) >= EMA_200_MIN_CANDLES
    if not enough_for_ema_200:
        raise DataError(
            f"Historical CSV has {len(filtered_candles)} candles after filtering; "
            f"at least {EMA_200_MIN_CANDLES} are required for EMA 200"
        )

    sorted_ascending = all(
        earlier < later for earlier, later in zip(input_timestamps, input_timestamps[1:])
    )
    gap_summary = _gap_summary(filtered_candles)
    warnings: list[str] = []
    if not sorted_ascending:
        warnings.append("Input rows are not sorted by ascending timestamp")
    if gap_summary.irregular_gap_count:
        warnings.append(f"Irregular candle gaps detected: {gap_summary.irregular_gap_count}")

    status = "WARN" if warnings else "PASS"
    first_timestamp = sorted_candles[0].timestamp
    last_timestamp = sorted_candles[-1].timestamp
    filtered_first = filtered_candles[0].timestamp
    filtered_last = filtered_candles[-1].timestamp

    return HistoricalDataReport(
        file_name=csv_path.name,
        total_rows=len(candles),
        valid_candle_count=len(candles),
        filtered_candle_count=len(filtered_candles),
        first_timestamp=first_timestamp.isoformat(),
        last_timestamp=last_timestamp.isoformat(),
        filtered_first_timestamp=filtered_first.isoformat(),
        filtered_last_timestamp=filtered_last.isoformat(),
        date_range_days=(filtered_last.date() - filtered_first.date()).days + 1,
        symbol="BTC",
        has_optional_timeframe_column=has_timeframe,
        timeframe_values_seen=tuple(sorted(timeframe_values)),
        has_optional_source_column=has_source,
        source_values_seen=tuple(sorted(source_values)),
        duplicate_timestamp_count=0,
        sorted_ascending=sorted_ascending,
        minimum_close=min(candle.close for candle in filtered_candles),
        maximum_close=max(candle.close for candle in filtered_candles),
        minimum_volume=min(candle.volume for candle in filtered_candles),
        maximum_volume=max(candle.volume for candle in filtered_candles),
        enough_for_ema_200=enough_for_ema_200,
        detected_interval_seconds=gap_summary.detected_interval_seconds,
        irregular_gap_count=gap_summary.irregular_gap_count,
        largest_gap_seconds=gap_summary.largest_gap_seconds,
        status=status,
        reasons=(),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True, slots=True)
class _GapSummary:
    detected_interval_seconds: int | None
    irregular_gap_count: int
    largest_gap_seconds: int | None


def _filter_candles(candles: Sequence[Candle], start: date | None, end: date | None) -> list[Candle]:
    return [
        candle
        for candle in candles
        if (start is None or candle.timestamp.date() >= start)
        and (end is None or candle.timestamp.date() <= end)
    ]


def _gap_summary(candles: Sequence[Candle]) -> _GapSummary:
    if len(candles) < 2:
        return _GapSummary(detected_interval_seconds=None, irregular_gap_count=0, largest_gap_seconds=None)

    deltas = [
        int((later.timestamp - earlier.timestamp).total_seconds())
        for earlier, later in zip(candles, candles[1:])
    ]
    largest_gap_seconds = max(deltas)
    counts = Counter(deltas)
    detected_interval, expected_count = counts.most_common(1)[0]
    if len(counts) == 1:
        return _GapSummary(
            detected_interval_seconds=detected_interval,
            irregular_gap_count=0,
            largest_gap_seconds=largest_gap_seconds,
        )
    return _GapSummary(
        detected_interval_seconds=None,
        irregular_gap_count=len(deltas) - expected_count,
        largest_gap_seconds=largest_gap_seconds,
    )


def _format_missing_columns(missing_columns: set[str]) -> str:
    ordered = [column for column in REQUIRED_CANDLE_COLUMNS if column in missing_columns]
    return ", ".join(ordered)
