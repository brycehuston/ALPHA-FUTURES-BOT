"""ALPHA-FUTURES-BOT safe V1 package skeleton."""

from alpha_futures_bot.broker import BrokerBase, BrokerError, PaperBroker
from alpha_futures_bot.config import BotConfig, ConfigError, RiskSettings, default_config, load_config
from alpha_futures_bot.indicators import IndicatorSnapshot, calculate_indicators
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
from alpha_futures_bot.risk import RiskDecision, evaluate_signal
from alpha_futures_bot.strategy import generate_signal

__all__ = [
    "BrokerBase",
    "BrokerError",
    "BotConfig",
    "BotMode",
    "Candle",
    "ClosedPosition",
    "ConfigError",
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
    "Signal",
    "SignalAction",
    "Symbol",
    "calculate_indicators",
    "default_config",
    "detect_regime",
    "evaluate_signal",
    "generate_signal",
    "load_config",
]
