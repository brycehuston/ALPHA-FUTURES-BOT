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

The simulation writes local CSV logs only:

- `logs/scans.csv`
- `logs/trades.csv`

No live trading, testnet trading, exchange SDKs, exchange URLs, network calls, API keys, wallets, private keys, secrets, or `.env` loading are used.
