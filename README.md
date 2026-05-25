# ALPHA-FUTURES-BOT

ALPHA-FUTURES-BOT is a BTC-only, paper/test-first Python project.

V1 is intentionally limited:

- No live trading.
- No mainnet or real-money execution.
- No exchange SDKs, private keys, wallets, or `.env` loading.
- No ML, news trading, range mode, or breakout mode.

Phase 1 contains only the safe package skeleton, typed models, and config validation.

## Local Usage

Install test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the offline test suite:

```powershell
python -m pytest -p no:cacheprovider
```

Run the local paper simulation with synthetic BTC candles:

```powershell
python -m alpha_futures_bot.runner --candles data/sample_btc_candles.csv --logs logs
```

The simulation writes local CSV logs only:

- `logs/scans.csv`
- `logs/trades.csv`

No live trading, testnet trading, exchange SDKs, network calls, secrets, wallets, private keys, or `.env` loading are used.
