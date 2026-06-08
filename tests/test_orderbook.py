from microstructurelab.models import OrderRequest, OrderType, Side, TimeInForce
from microstructurelab.orderbook import MatchingEngine


def test_price_time_matching():
    engine = MatchingEngine()
    engine.submit(OrderRequest("s1", "c1", "AAPL", Side.SELL, OrderType.LIMIT, 100, 101, TimeInForce.GTC).to_order(1))
    result = engine.submit(OrderRequest("b1", "c2", "AAPL", Side.BUY, OrderType.LIMIT, 50, 101, TimeInForce.GTC).to_order(2))
    assert len(result.trades) == 1
    assert result.trades[0].price == 101
    assert result.trades[0].quantity == 50


def test_cancel_order():
    engine = MatchingEngine()
    engine.submit(OrderRequest("b1", "c1", "AAPL", Side.BUY, OrderType.LIMIT, 100, 99, TimeInForce.GTC).to_order(1))
    result = engine.cancel("AAPL", "b1", 2)
    assert result.reports[0].status.value == "CANCELLED"
