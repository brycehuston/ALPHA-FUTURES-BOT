"""Local CSV candle loading for offline BTC paper simulations."""

from __future__ import annotations

import csv
from datetime import datetime
from math import isfinite
from pathlib import Path

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
        if tuple(reader.fieldnames) != REQUIRED_CANDLE_COLUMNS:
            raise DataError("Candle CSV columns must match required V1 schema")

        candles: list[Candle] = []
        seen_timestamps: set[datetime] = set()
        for row_number, row in enumerate(reader, start=2):
            candle = _parse_row(row, row_number)
            if candle.timestamp in seen_timestamps:
                raise DataError(f"Duplicate candle timestamp on row {row_number}")
            seen_timestamps.add(candle.timestamp)
            candles.append(candle)

    return sorted(candles, key=lambda candle: candle.timestamp)


def _parse_row(row: dict[str, str], row_number: int) -> Candle:
    try:
        timestamp = datetime.fromisoformat(row["timestamp"])
    except (TypeError, ValueError) as exc:
        raise DataError(f"Invalid timestamp on row {row_number}") from exc

    symbol = row["symbol"].strip().upper()
    if symbol != Symbol.BTC.value:
        raise DataError(f"Unsupported symbol on row {row_number}")

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
        raise DataError(f"Invalid {name} on row {row_number}") from exc
    if not isfinite(parsed):
        raise DataError(f"Invalid {name} on row {row_number}")
    return parsed


def _validate_ohlcv(open_price: float, high: float, low: float, close: float, volume: float, row_number: int) -> None:
    if min(open_price, high, low, close) <= 0:
        raise DataError(f"OHLC prices must be greater than zero on row {row_number}")
    if volume < 0:
        raise DataError(f"Volume must be non-negative on row {row_number}")
    if high < low:
        raise DataError(f"High must be greater than or equal to low on row {row_number}")
    if high < max(open_price, close):
        raise DataError(f"High must cover open and close on row {row_number}")
    if low > min(open_price, close):
        raise DataError(f"Low must cover open and close on row {row_number}")
