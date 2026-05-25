"""Local CSV candle loading for offline BTC paper simulations."""

from __future__ import annotations

import csv
from datetime import date, datetime
from math import isfinite
from pathlib import Path
from typing import Sequence

from alpha_futures_bot.models import Candle, Symbol

REQUIRED_CANDLE_COLUMNS = ("timestamp", "symbol", "open", "high", "low", "close", "volume")


class DataError(ValueError):
    """Raised when local candle data cannot be safely loaded."""


def load_candles_from_csv(path: str | Path) -> list[Candle]:
    """Load BTC candles from a local CSV file, failing closed on malformed rows."""

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
        seen_timestamps: set[datetime] = set()
        for row_number, row in enumerate(reader, start=2):
            candle = parse_candle_row(row, row_number)
            if candle.timestamp in seen_timestamps:
                raise DataError(f"Duplicate timestamp found: {candle.timestamp.isoformat()}")
            seen_timestamps.add(candle.timestamp)
            candles.append(candle)

    if not candles:
        raise DataError("Empty CSV: no candle rows found")
    return sorted(candles, key=lambda candle: candle.timestamp)


def parse_backtest_date(value: str | None) -> date | None:
    """Parse an optional YYYY-MM-DD backtest date, failing closed on malformed input."""

    if value is None:
        return None
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise DataError("Backtest dates must use YYYY-MM-DD format")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise DataError("Backtest dates must use YYYY-MM-DD format") from exc


def filter_candles_by_date_range(
    candles: Sequence[Candle],
    start: date | None = None,
    end: date | None = None,
) -> list[Candle]:
    """Return candles inside inclusive calendar-date boundaries."""

    if start is not None and end is not None and start > end:
        raise DataError("Backtest start date must be before or equal to end date")

    filtered = [
        candle
        for candle in candles
        if (start is None or candle.timestamp.date() >= start)
        and (end is None or candle.timestamp.date() <= end)
    ]
    if not filtered:
        raise DataError("Empty CSV after date filtering")
    return sorted(filtered, key=lambda candle: candle.timestamp)


def parse_candle_row(row: dict[str, str], row_number: int) -> Candle:
    """Parse one local BTC candle CSV row, failing closed on malformed values."""

    try:
        timestamp = datetime.fromisoformat(row["timestamp"])
    except (TypeError, ValueError) as exc:
        raise DataError(f"Invalid timestamp at row {row_number}") from exc

    symbol = (row["symbol"] or "").strip().upper()
    if symbol != Symbol.BTC.value:
        raise DataError(f"Non-BTC symbol found at row {row_number}: {symbol}")

    open_price = _parse_float(row["open"], "open", row_number)
    high = _parse_float(row["high"], "high", row_number)
    low = _parse_float(row["low"], "low", row_number)
    close = _parse_float(row["close"], "close", row_number)
    volume = _parse_float(row["volume"], "volume", row_number)

    _validate_ohlcv(open_price, high, low, close, volume, row_number)
    return Candle(
        symbol=Symbol.BTC,
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _parse_float(value: str, name: str, row_number: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise DataError(f"Invalid OHLCV at row {row_number}: {name} is not a number") from exc
    if not isfinite(parsed):
        raise DataError(f"Invalid OHLCV at row {row_number}: {name} is not a finite number")
    return parsed


def _validate_ohlcv(open_price: float, high: float, low: float, close: float, volume: float, row_number: int) -> None:
    if min(open_price, high, low, close) <= 0:
        raise DataError(f"Invalid OHLCV at row {row_number}: OHLC prices must be greater than zero")
    if volume < 0:
        raise DataError(f"Invalid OHLCV at row {row_number}: volume is negative")
    if high < low:
        raise DataError(f"Invalid OHLCV at row {row_number}: high is below low")
    if high < max(open_price, close):
        raise DataError(f"Invalid OHLCV at row {row_number}: high is below open or close")
    if low > min(open_price, close):
        raise DataError(f"Invalid OHLCV at row {row_number}: low is above open or close")


def _format_missing_columns(missing_columns: set[str]) -> str:
    ordered = [column for column in REQUIRED_CANDLE_COLUMNS if column in missing_columns]
    return ", ".join(ordered)
