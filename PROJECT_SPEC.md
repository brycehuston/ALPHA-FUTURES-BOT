# ALPHA-FUTURES-BOT PROJECT SPEC

Date basis: May 2026

## 1. Project Name

ALPHA-FUTURES-BOT

This project is a paper/testnet-first Python crypto futures regime bot.

V1 is intentionally simple, safe, modular, and exchange-agnostic.

---

## 2. Core Safety Rules

This project must stay safe and testnet/paper-first.

Hard rules:

1. No live trading in V1.
2. No real-money execution in V1.
3. No live leveraged trading logic may be enabled.
4. Do not add mainnet private key support.
5. Do not add withdrawal support.
6. Do not bypass age limits, KYC, platform rules, laws, or geo restrictions.
7. Do not add code that helps bypass exchange limits, compliance checks, or regional restrictions.
8. Any broker capable of real execution is out of scope for V1.
9. Hyperliquid testnet may be added later only as a sandbox adapter.
10. V1 must use `BrokerBase` and `PaperBroker` first.
11. `HyperliquidTestnetBroker` is future work, not V1.
12. Every trade must be simulated unless a future testnet adapter is explicitly created and reviewed.
13. Any accidental live-trading path must fail closed.

Fail closed means:

- If broker mode is unknown, stop.
- If config says live trading, stop.
- If real API keys are detected in V1, stop.
- If order sizing is invalid, stop.
- If risk settings are missing, stop.
- If data is stale, stop.
- If required indicators are unavailable, stop.

---

## 3. V1 Scope

V1 includes:

- BTC only
- Paper trading first
- No live trading
- No real-money execution
- No ML
- No news trading
- No range mode
- No breakout mode
- Exchange-agnostic architecture
- Broker abstraction
- Paper broker
- Position manager
- Risk engine
- Regime detection
- Trend pullback long setup
- Trend pullback short setup
- Signal score
- Scan logging
- Trade logging
- Local historical BTC CSV support
- Optional historical CSV metadata columns
- Inclusive date range filtering
- Multi-file local comparison
- Reporting metrics
- Summary and comparison JSON reports
- Strategy presets
- Preset comparison
- Local historical CSV validation command
- Historical data sanity report
- Unit tests

---

## 4. Future Scope

These are allowed later, but must not be built in V1:

- ETH support
- SOL support
- Hyperliquid testnet adapter
- Range mode
- Breakout mode
- News filters
- ML filters
- Live execution
- Mainnet execution
- Multi-exchange routing
- Advanced portfolio sizing
- Dashboard
- Web UI
- Database
- Cloud deployment

Do not overbuild V1.

---

## 5. Main Goal

The goal of V1 is to build a safe, testable BTC paper-trading bot that can:

1. Load historical or mocked candle data.
2. Calculate indicators.
3. Detect market regime.
4. Decide whether BTC is in:
   - `BULL_TREND`
   - `BEAR_TREND`
   - `NO_TRADE`
5. Detect a trend pullback long setup during `BULL_TREND`.
6. Detect a trend pullback short setup during `BEAR_TREND`.
7. Score the signal.
8. Pass the signal through a risk engine.
9. Open, manage, and close paper positions.
10. Log scans and paper trades.
11. Produce local summary and comparison reports.
12. Validate user-provided local BTC historical CSV files before backtests.
13. Pass unit tests.

---

## 6. Bot Modes

V1 supports only these modes:

```txt
PAPER
TEST
```
