from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Set

from .models import Order, Side, Trade


@dataclass(slots=True)
class RiskLimits:
    max_order_qty: int = 50_000
    max_notional: int = 25_000_000
    max_abs_position: int = 100_000
    max_price_deviation_bps: int = 1_000
    max_orders_per_client: int = 250_000
    allowed_symbols: set[str] = field(default_factory=lambda: {"AAPL", "MSFT", "NVDA", "AMZN"})


@dataclass(slots=True)
class RiskDecision:
    accepted: bool
    reason: str = ""


class RiskEngine:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()
        self.positions: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.order_counts: DefaultDict[str, int] = defaultdict(int)
        self.disabled_clients: Set[str] = set()
        self.rejections = 0

    def disable_client(self, client_id: str) -> None:
        self.disabled_clients.add(client_id)

    def enable_client(self, client_id: str) -> None:
        self.disabled_clients.discard(client_id)

    def check(self, order: Order, reference_price: int | None = None) -> RiskDecision:
        if order.client_id in self.disabled_clients:
            return self._reject(f"client {order.client_id} is disabled")
        if self.order_counts[order.client_id] >= self.limits.max_orders_per_client:
            return self._reject(f"client {order.client_id} exceeded order throttle")
        if order.symbol not in self.limits.allowed_symbols:
            return self._reject(f"symbol {order.symbol} is not enabled")
        if order.quantity > self.limits.max_order_qty:
            return self._reject(f"quantity {order.quantity} exceeds max_order_qty {self.limits.max_order_qty}")
        price = order.price or reference_price
        if price is None:
            return self._reject("market order requires a reference price")
        if reference_price and order.price:
            deviation_bps = abs(order.price - reference_price) * 10_000 // reference_price
            if deviation_bps > self.limits.max_price_deviation_bps:
                return self._reject(f"price deviation {deviation_bps} bps exceeds limit")
        if price * order.quantity > self.limits.max_notional:
            return self._reject("notional exceeds limit")
        current = self.positions[order.client_id][order.symbol]
        projected = current + order.side.sign * order.quantity
        if abs(projected) > self.limits.max_abs_position:
            return self._reject("projected position exceeds limit")
        self.order_counts[order.client_id] += 1
        return RiskDecision(True, "accepted")

    def on_trade(self, trade: Trade) -> None:
        if trade.aggressor_side == Side.BUY:
            buyer, seller = trade.taker_client_id, trade.maker_client_id
        else:
            buyer, seller = trade.maker_client_id, trade.taker_client_id
        self.positions[buyer][trade.symbol] += trade.quantity
        self.positions[seller][trade.symbol] -= trade.quantity

    def position_snapshot(self) -> Dict[str, Dict[str, int]]:
        return {client: dict(symbols) for client, symbols in self.positions.items()}

    def risk_snapshot(self) -> Dict[str, object]:
        return {"positions": self.position_snapshot(), "order_counts": dict(self.order_counts), "disabled_clients": sorted(self.disabled_clients), "rejections": self.rejections}

    def _reject(self, reason: str) -> RiskDecision:
        self.rejections += 1
        return RiskDecision(False, reason)
