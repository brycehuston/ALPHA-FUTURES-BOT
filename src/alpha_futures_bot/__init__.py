"""ALPHA-FUTURES-BOT safe V1 package skeleton."""

from alpha_futures_bot.broker import BrokerBase, BrokerError, PaperBroker
from alpha_futures_bot.config import BotConfig, ConfigError, RiskSettings, default_config, load_config
from alpha_futures_bot.data import DataError, filter_candles_by_date_range, load_candles_from_csv, parse_backtest_date
from alpha_futures_bot.indicators import IndicatorSnapshot, calculate_indicators
from alpha_futures_bot.logging_service import SimulationLogger
from alpha_futures_bot.models import (
    BotMode,
    Candle,
    ClosedPosition,
    OrderRequest,
    PaperPosition,
    Regime,
    Side,
    Signal,
    SignalAction,
    Symbol,
)
from alpha_futures_bot.position import PositionDecision, PositionManager, PositionUpdate
from alpha_futures_bot.regime import detect_regime
from alpha_futures_bot.reporting import (
    BacktestComparisonReport,
    BacktestComparisonRow,
    BacktestReport,
    build_backtest_report,
    build_comparison_report,
    build_comparison_row,
)
from alpha_futures_bot.risk import RiskDecision, evaluate_signal
from alpha_futures_bot.strategy import generate_signal

__all__ = [
    "BrokerBase",
    "BrokerError",
    "BacktestComparisonReport",
    "BacktestComparisonRow",
    "BacktestReport",
    "BotConfig",
    "BotMode",
    "Candle",
    "ClosedPosition",
    "ConfigError",
    "DataError",
    "IndicatorSnapshot",
    "OrderRequest",
    "PaperBroker",
    "PaperPosition",
    "PositionDecision",
    "PositionManager",
    "PositionUpdate",
    "Regime",
    "RiskDecision",
    "RiskSettings",
    "Side",
    "SimulationLogger",
    "Signal",
    "SignalAction",
    "Symbol",
    "calculate_indicators",
    "build_backtest_report",
    "build_comparison_report",
    "build_comparison_row",
    "default_config",
    "detect_regime",
    "evaluate_signal",
    "filter_candles_by_date_range",
    "generate_signal",
    "load_candles_from_csv",
    "load_config",
    "parse_backtest_date",
]
