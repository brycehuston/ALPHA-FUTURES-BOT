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
from alpha_futures_bot.presets import (
    BALANCED_PRESET,
    LOOSE_PRESET,
    PRESET_NAMES,
    PRESETS,
    STRICT_PRESET,
    PresetError,
    StrategySettings,
    get_preset,
)
from alpha_futures_bot.regime import detect_regime
from alpha_futures_bot.reporting import (
    BacktestComparisonReport,
    BacktestComparisonRow,
    BacktestReport,
    PresetComparisonReport,
    PresetComparisonRow,
    build_backtest_report,
    build_comparison_report,
    build_comparison_row,
    build_preset_comparison_report,
    build_preset_comparison_row,
)
from alpha_futures_bot.risk import RiskDecision, evaluate_signal
from alpha_futures_bot.strategy import generate_signal

__all__ = [
    "BrokerBase",
    "BrokerError",
    "BALANCED_PRESET",
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
    "PresetComparisonReport",
    "PresetComparisonRow",
    "PresetError",
    "PRESET_NAMES",
    "PRESETS",
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
    "StrategySettings",
    "STRICT_PRESET",
    "LOOSE_PRESET",
    "Symbol",
    "calculate_indicators",
    "build_backtest_report",
    "build_comparison_report",
    "build_comparison_row",
    "build_preset_comparison_report",
    "build_preset_comparison_row",
    "default_config",
    "detect_regime",
    "evaluate_signal",
    "filter_candles_by_date_range",
    "generate_signal",
    "get_preset",
    "load_candles_from_csv",
    "load_config",
    "parse_backtest_date",
]
