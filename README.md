# ALPHA-FUTURES-BOT

ALPHA-FUTURES-BOT is a BTC-only, local paper-simulation Python project.

V1 is intentionally limited and offline:

- BTC-only.
- Local paper simulation only.
- No live trading.
- No testnet trading.
- No mainnet or real-money execution.
- No exchange SDKs.
- No exchange URLs.
- No API keys.
- No wallets.
- No private keys.
- No `.env` loading.
- No network calls.
- No ML, news trading, range mode, or breakout mode.

V1 includes local CSV candle loading, deterministic indicators/regime detection, broker-free strategy signals, a fail-closed risk engine, an in-memory `PaperBroker`, a basic position manager, and local CSV scan/trade logs.

## Local Usage

Install test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the offline test suite:

```powershell
python -m pytest -p no:cacheprovider --basetemp=.pytest_tmp
```

Run the local paper simulation with synthetic BTC candles:

```powershell
python -m alpha_futures_bot.runner --candles data/sample_btc_candles.csv --logs logs
```

Run with an explicit local strategy preset:

```powershell
python -m alpha_futures_bot.runner --candles data/sample_btc_candles.csv --logs logs --preset balanced
```

Run a local historical BTC CSV over an inclusive date range:

```powershell
python -m alpha_futures_bot.runner --candles data/history/btc_1h.csv --logs logs --start 2024-01-01 --end 2024-12-31
```

Compare multiple local BTC CSV files:

```powershell
python -m alpha_futures_bot.runner --candles data/history/btc_2023.csv data/history/btc_2024.csv --logs logs
```

Compare all local strategy presets on one BTC CSV:

```powershell
python -m alpha_futures_bot.runner --candles data/history/btc_1h.csv --logs logs --compare-presets
```

Historical CSV files must include:

- `timestamp`
- `symbol`
- `open`
- `high`
- `low`
- `close`
- `volume`

Optional metadata columns such as `timeframe` or `source` may exist and are ignored in V1. Historical CSV files are user-provided local files only; the bot never downloads or fetches market data.

Single-file simulations write:

- `logs/scans.csv`
- `logs/trades.csv`
- `logs/summary.json`

Multi-file comparisons write isolated per-run logs under `logs/runs/<safe_file_stem>/` and a combined `logs/comparison.json`.

Local strategy presets are fixed constants for offline research only:

- `strict`: higher minimum score and tighter confirmations.
- `balanced`: current default behavior.
- `loose`: lower minimum score and lighter confirmations.

Preset comparisons write isolated per-preset logs under `logs/presets/<preset>/` and a combined `logs/preset_comparison.json`.

The summary report includes return percentage, win rate, profit factor, max drawdown, equity high/low, average trade PnL, and best/worst trade.

No live trading, testnet trading, exchange SDKs, exchange URLs, network calls, API keys, wallets, private keys, secrets, or `.env` loading are used.
