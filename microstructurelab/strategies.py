from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import OrderRequest, OrderType, Side, TimeInForce
from .scenarios import next_order_id


@dataclass
class MarketMakerStrategy:
    client_id: str = "market-maker"
    symbol: str = "AAPL"
    size: int = 100
    spread_ticks: int = 2

    def quote(self, mid_price: int) -> List[OrderRequest]:
        half = max(1, self.spread_ticks // 2)
        return [
            OrderRequest(next_order_id("MMB"), self.client_id, self.symbol, Side.BUY, OrderType.LIMIT, self.size, mid_price - half, TimeInForce.GTC),
            OrderRequest(next_order_id("MMA"), self.client_id, self.symbol, Side.SELL, OrderType.LIMIT, self.size, mid_price + half, TimeInForce.GTC),
        ]


@dataclass
class TwapStrategy:
    client_id: str = "twap"
    symbol: str = "AAPL"
    side: Side = Side.BUY
    total_quantity: int = 1_000
    slices: int = 10

    def orders(self, price: int) -> List[OrderRequest]:
        qty = max(1, self.total_quantity // self.slices)
        return [OrderRequest(next_order_id("TWAP"), self.client_id, self.symbol, self.side, OrderType.LIMIT, qty, price, TimeInForce.IOC) for _ in range(self.slices)]
