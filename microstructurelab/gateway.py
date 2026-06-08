from __future__ import annotations

from time import time_ns
from typing import List

from .journal import EventJournal
from .models import ExecutionReport, MatchResult, OrderRequest, OrderStatus, ReplaceRequest, Trade
from .orderbook import MatchingEngine
from .risk import RiskEngine


class OrderGateway:
    def __init__(self, matching_engine: MatchingEngine | None = None, risk_engine: RiskEngine | None = None) -> None:
        self.matching_engine = matching_engine or MatchingEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.journal = EventJournal()
        self.trades: List[Trade] = []
        self.reports: List[ExecutionReport] = []

    def submit(self, request: OrderRequest) -> MatchResult:
        now = time_ns()
        order = request.to_order(timestamp_ns=now)
        decision = self.risk_engine.check(order, reference_price=self._reference_price(order.symbol))
        if not decision.accepted:
            report = ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.REJECTED, price=order.price, message=decision.reason, timestamp_ns=now)
            result = MatchResult([report], [], [], 0)
            self._record(result)
            return result
        result = self.matching_engine.submit(order)
        for trade in result.trades:
            self.risk_engine.on_trade(trade)
        self._record(result)
        return result

    def cancel(self, symbol: str, order_id: str) -> MatchResult:
        result = self.matching_engine.cancel(symbol, order_id, time_ns())
        self._record(result)
        return result

    def replace(self, request: ReplaceRequest) -> MatchResult:
        old_order = self.matching_engine.get_book(request.symbol).order_index.get(request.order_id)
        if old_order is None:
            result = self.matching_engine.cancel(request.symbol, request.order_id, time_ns())
            self._record(result)
            return result
        new_request = OrderRequest(request.new_order_id, request.client_id, request.symbol, old_order.side, old_order.order_type, request.quantity, request.price, request.time_in_force, request.post_only)
        now = time_ns()
        new_order = new_request.to_order(now)
        decision = self.risk_engine.check(new_order, reference_price=self._reference_price(request.symbol))
        if not decision.accepted:
            report = ExecutionReport(request.new_order_id, request.client_id, request.symbol, OrderStatus.REJECTED, price=request.price, message=decision.reason, timestamp_ns=now)
            result = MatchResult([report], [], [], 0)
            self._record(result)
            return result
        result = self.matching_engine.replace(request.symbol, request.order_id, new_order)
        for trade in result.trades:
            self.risk_engine.on_trade(trade)
        self._record(result)
        return result

    def _record(self, result: MatchResult) -> None:
        self.trades.extend(result.trades)
        self.reports.extend(result.reports)
        self.journal.record_reports(result.reports)
        self.journal.record_trades(result.trades)
        self.journal.record_market_data(result.market_data)

    def _reference_price(self, symbol: str) -> int | None:
        snapshot = self.matching_engine.snapshot(symbol)
        if snapshot.best_bid and snapshot.best_ask:
            return (snapshot.best_bid + snapshot.best_ask) // 2
        return snapshot.best_bid or snapshot.best_ask

    def positions(self):
        return self.risk_engine.position_snapshot()

    def risk(self):
        return self.risk_engine.risk_snapshot()
