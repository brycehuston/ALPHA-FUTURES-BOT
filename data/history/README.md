# Local Historical BTC CSV Files

Place user-provided BTC historical CSV files in this folder.

Required columns:

```csv
timestamp,symbol,open,high,low,close,volume
2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10
```

Optional metadata columns are accepted:

```csv
timestamp,symbol,open,high,low,close,volume,timeframe,source
2024-01-01T00:00:00+00:00,BTC,100,101,99,100,10,1h,manual
```

The example values above are synthetic. Real historical CSV files are local and user-provided only. The bot does not download data, fetch exchange data, call APIs, or fill missing candles.

Validate a file before running it:

```powershell
python -m alpha_futures_bot.runner --validate-csv data/history/btc_1h.csv
```

CSV files in this folder are ignored by git. Keep `data/sample_btc_candles.csv` for tracked smoke tests.
