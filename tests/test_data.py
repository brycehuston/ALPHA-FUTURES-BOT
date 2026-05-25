from __future__ import annotations

from pathlib import Path

import pytest

from alpha_futures_bot.data import DataError, load_candles_from_csv


def test_loads_valid_local_btc_csv(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        [
            "2026-01-01T00:00:00+00:00,BTC,100,101,99,100,10",
            "2026-01-01T00:01:00+00:00,BTC,101,102,100,101,11",
        ],
    )

    candles = load_candles_from_csv(path)

    assert len(candles) == 2
    assert candles[0].symbol.value == "BTC"
    assert candles[0].close == 100.0


def test_sorts_rows_by_timestamp(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        [
            "2026-01-01T00:01:00+00:00,BTC,101,102,100,101,11",
            "2026-01-01T00:00:00+00:00,BTC,100,101,99,100,10",
        ],
    )

    candles = load_candles_from_csv(path)

    assert candles[0].close == 100.0
    assert candles[1].close == 101.0


def test_rejects_missing_required_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("timestamp,symbol,open,high,low,close\n2026-01-01T00:00:00+00:00,BTC,100,101,99,100\n")

    with pytest.raises(DataError, match="Missing required columns: volume"):
        load_candles_from_csv(path)


def test_rejects_non_btc_symbols(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, ["2026-01-01T00:00:00+00:00,ETH,100,101,99,100,10"])

    with pytest.raises(DataError, match="Non-BTC symbol found at row 2: ETH"):
        load_candles_from_csv(path)


def test_rejects_duplicate_timestamps(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        [
            "2026-01-01T00:00:00+00:00,BTC,100,101,99,100,10",
            "2026-01-01T00:00:00+00:00,BTC,101,102,100,101,11",
        ],
    )

    with pytest.raises(DataError, match="Duplicate timestamp found: 2026-01-01T00:00:00\\+00:00"):
        load_candles_from_csv(path)


@pytest.mark.parametrize(
    "row",
    [
        "2026-01-01T00:00:00+00:00,BTC,0,101,99,100,10",
        "2026-01-01T00:00:00+00:00,BTC,100,98,99,100,10",
        "2026-01-01T00:00:00+00:00,BTC,100,101,99,100,-1",
        "2026-01-01T00:00:00+00:00,BTC,100,nan,99,100,10",
    ],
)
def test_rejects_invalid_ohlcv_values(tmp_path: Path, row: str) -> None:
    path = _write_csv(tmp_path, [row])

    with pytest.raises(DataError, match="Invalid OHLCV at row 2"):
        load_candles_from_csv(path)


def test_rejects_malformed_timestamp(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, ["not-a-date,BTC,100,101,99,100,10"])

    with pytest.raises(DataError, match="Invalid timestamp at row 2"):
        load_candles_from_csv(path)


def test_rejects_header_only_csv(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("timestamp,symbol,open,high,low,close,volume\n", encoding="utf-8")

    with pytest.raises(DataError, match="Empty CSV: no candle rows found"):
        load_candles_from_csv(path)


def test_loader_has_no_network_dependency() -> None:
    source = Path("src/alpha_futures_bot/data.py").read_text(encoding="utf-8").lower()

    assert "requests" not in source
    assert "httpx" not in source
    assert "urlopen" not in source
    assert "socket" not in source


def _write_csv(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "candles.csv"
    path.write_text("timestamp,symbol,open,high,low,close,volume\n" + "\n".join(rows) + "\n")
    return path
