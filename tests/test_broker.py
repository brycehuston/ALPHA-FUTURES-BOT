from __future__ import annotations

from datetime import datetime, timezone

import pytest

from alpha_futures_bot.broker import BrokerError, PaperBroker
from alpha_futures_bot.models import Candle, OrderRequest, Side, Symbol


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_paper_broker_opens_one_simulated_btc_position() -> None:
    from conftest import make_long_order

    broker = PaperBroker()
    position = broker.submit_order(make_long_order(), NOW)

    assert position.symbol is Symbol.BTC
    assert broker.get_open_position(Symbol.BTC) == position


def test_duplicate_btc_position_is_rejected() -> None:
    from conftest import make_long_order

    broker = PaperBroker()
    broker.submit_order(make_long_order(), NOW)

    with pytest.raises(BrokerError):
        broker.submit_order(make_long_order(), NOW)


def test_long_close_updates_realized_pnl_and_cash() -> None:
    from conftest import make_long_order

    broker = PaperBroker(starting_balance=10_000.0)
    broker.submit_order(make_long_order(), NOW)
    closed = broker.close_position(Symbol.BTC, 110.0, NOW, "manual")

    assert closed.realized_pnl == 10.0
    assert broker.realized_pnl == 10.0
    assert broker.cash_balance == 10_010.0


def test_short_close_updates_realized_pnl_and_cash() -> None:
    from conftest import make_short_order

    broker = PaperBroker(starting_balance=10_000.0)
    broker.submit_order(make_short_order(), NOW)
    closed = broker.close_position(Symbol.BTC, 90.0, NOW, "manual")

    assert closed.realized_pnl == 10.0
    assert broker.cash_balance == 10_010.0


def test_unrealized_pnl_is_deterministic() -> None:
    from conftest import make_long_order, make_short_order

    long_broker = PaperBroker()
    long_broker.submit_order(make_long_order(), NOW)
    short_broker = PaperBroker()
    short_broker.submit_order(make_short_order(), NOW)

    assert long_broker.mark_to_market(Symbol.BTC, 105.0) == 5.0
    assert short_broker.mark_to_market(Symbol.BTC, 95.0) == 5.0


def test_long_stop_and_take_profit_close_positions() -> None:
    from conftest import make_long_order

    stop_broker = PaperBroker()
    stop_broker.submit_order(make_long_order(), NOW)
    stopped = stop_broker.update_from_candle(_candle(low=94.0, high=104.0))

    profit_broker = PaperBroker()
    profit_broker.submit_order(make_long_order(), NOW)
    profited = profit_broker.update_from_candle(_candle(low=99.0, high=111.0))

    assert stopped is not None
    assert stopped.close_reason == "stop_loss"
    assert stopped.exit_price == 95.0
    assert profited is not None
    assert profited.close_reason == "take_profit"
    assert profited.exit_price == 110.0


def test_short_stop_and_take_profit_close_positions() -> None:
    from conftest import make_short_order

    stop_broker = PaperBroker()
    stop_broker.submit_order(make_short_order(), NOW)
    stopped = stop_broker.update_from_candle(_candle(low=96.0, high=106.0))

    profit_broker = PaperBroker()
    profit_broker.submit_order(make_short_order(), NOW)
    profited = profit_broker.update_from_candle(_candle(low=89.0, high=101.0))

    assert stopped is not None
    assert stopped.close_reason == "stop_loss"
    assert stopped.exit_price == 105.0
    assert profited is not None
    assert profited.close_reason == "take_profit"
    assert profited.exit_price == 90.0


def test_same_candle_stop_and_take_profit_chooses_stop_loss() -> None:
    from conftest import make_long_order

    broker = PaperBroker()
    broker.submit_order(make_long_order(), NOW)
    closed = broker.update_from_candle(_candle(low=94.0, high=111.0))

    assert closed is not None
    assert closed.close_reason == "stop_loss"
    assert closed.exit_price == 95.0


def test_invalid_order_values_are_rejected() -> None:
    broker = PaperBroker()
    invalid = OrderRequest(Symbol.BTC, Side.LONG, 0.0, 100.0, 95.0, 110.0)

    with pytest.raises(BrokerError):
        broker.submit_order(invalid, NOW)


def test_no_network_exchange_client_or_secret_attributes_exist() -> None:
    broker = PaperBroker()

    for name in ("network", "exchange", "client", "api_key", "secret", "wallet", "private_key"):
        assert not hasattr(broker, name)


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
