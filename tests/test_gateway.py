from microstructurelab.gateway import OrderGateway
from microstructurelab.models import OrderRequest, OrderType, Side, TimeInForce


def test_gateway_records_journal_events():
    gateway = OrderGateway()
    gateway.submit(OrderRequest("b1", "c1", "AAPL", Side.BUY, OrderType.LIMIT, 100, 99, TimeInForce.GTC))
    assert gateway.journal.events
    assert gateway.risk()["rejections"] == 0
