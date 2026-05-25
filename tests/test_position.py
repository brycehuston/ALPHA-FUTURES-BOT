from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alpha_futures_bot.broker import PaperBroker
from alpha_futures_bot.config import BotConfig, RiskSettings
from alpha_futures_bot.models import Candle, Symbol
from alpha_futures_bot.position import PositionManager


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_approved_signal_routes_to_paper_broker() -> None:
    from conftest import make_long_signal

    broker = PaperBroker()
    manager = PositionManager(broker)
    decision = manager.handle_signal(make_long_signal(), NOW)

    assert decision.accepted is True
    assert decision.position is not None
    assert broker.get_open_position(Symbol.BTC) is not None


def test_rejected_signal_is_not_submitted() -> None:
    from conftest import make_long_signal

    signal = make_long_signal()
    bad_signal = type(signal)(
        symbol=signal.symbol,
        action=signal.action,
        side=signal.side,
        score=1.0,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
    )
    broker = PaperBroker()
    decision = PositionManager(broker).handle_signal(bad_signal, NOW)

    assert decision.accepted is False
    assert broker.get_open_position(Symbol.BTC) is None


def test_duplicate_position_is_rejected() -> None:
    from conftest import make_long_signal

    broker = PaperBroker()
    manager = PositionManager(broker)
    assert manager.handle_signal(make_long_signal(), NOW).accepted is True

    duplicate = manager.handle_signal(make_long_signal(), NOW)

    assert duplicate.accepted is False


def test_max_open_positions_is_enforced() -> None:
    from conftest import make_long_order, make_short_signal

    broker = PaperBroker()
    broker.submit_order(make_long_order(), NOW)
    manager = PositionManager(broker, BotConfig(risk=RiskSettings(max_open_positions=1)))

    decision = manager.handle_signal(make_short_signal(), NOW)

    assert decision.accepted is False
    assert decision.reason == "max open positions reached"


def test_daily_loss_limit_rejection_passes_through() -> None:
    from conftest import make_long_signal

    decision = PositionManager(PaperBroker()).handle_signal(
        make_long_signal(),
        NOW,
        current_daily_loss=200.0,
    )

    assert decision.accepted is False


def test_candle_update_closes_on_stop_loss_and_take_profit() -> None:
    from conftest import make_long_signal

    stop_manager = PositionManager(PaperBroker())
    stop_manager.handle_signal(make_long_signal(), NOW)
    stopped = stop_manager.update_from_candle(_candle(low=94.0, high=104.0))

    profit_manager = PositionManager(PaperBroker())
    profit_manager.handle_signal(make_long_signal(), NOW)
    profited = profit_manager.update_from_candle(_candle(low=99.0, high=111.0))

    assert stopped.closed is True
    assert stopped.reason == "stop_loss"
    assert profited.closed is True
    assert profited.reason == "take_profit"


def test_invalid_non_btc_candle_update_fails_closed() -> None:
    from conftest import make_long_signal

    manager = PositionManager(PaperBroker())
    manager.handle_signal(make_long_signal(), NOW)
    update = manager.update_from_candle(
        Candle("ETH", NOW, open=100.0, high=101.0, low=99.0, close=100.0, volume=100.0)
    )

    assert update.closed is False


def test_position_manager_does_not_call_strategy_generation() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "alpha_futures_bot" / "position.py").read_text(
        encoding="utf-8"
    )

    assert "generate_signal" not in source
    assert "alpha_futures_bot.strategy" not in source
    assert "alpha_futures_bot.indicators" not in source
    assert "alpha_futures_bot.regime" not in source


def _candle(low: float, high: float) -> Candle:
    return Candle(
        symbol=Symbol.BTC,
        timestamp=NOW,
        open=100.0,
        high=high,
        low=low,
        close=100.0,
        volume=100.0,
    )
