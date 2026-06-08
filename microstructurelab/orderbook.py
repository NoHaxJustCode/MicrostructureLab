from __future__ import annotations

import heapq
from collections import defaultdict, deque
from time import perf_counter_ns
from typing import Deque, Dict, List, Optional
from uuid import uuid4

from .models import (
    BookLevel,
    BookSnapshot,
    EventType,
    ExecutionReport,
    MarketDataEvent,
    MatchResult,
    Order,
    OrderStatus,
    OrderType,
    Side,
    TimeInForce,
    Trade,
)


class LimitOrderBook:
    """Price-time priority limit order book for one symbol."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.bids: Dict[int, Deque[Order]] = defaultdict(deque)
        self.asks: Dict[int, Deque[Order]] = defaultdict(deque)
        self._bid_heap: List[int] = []
        self._ask_heap: List[int] = []
        self.order_index: Dict[str, Order] = {}
        self.sequence = 0

    def submit(self, order: Order) -> MatchResult:
        started = perf_counter_ns()
        reports: List[ExecutionReport] = []
        trades: List[Trade] = []

        if order.symbol != self.symbol:
            reports.append(ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.REJECTED, price=order.price, message="wrong symbol", timestamp_ns=order.timestamp_ns))
            return MatchResult(reports, trades, [], perf_counter_ns() - started)

        if order.post_only and self._would_cross(order):
            reports.append(ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.REJECTED, price=order.price, message="post-only would cross", timestamp_ns=order.timestamp_ns))
            return MatchResult(reports, trades, [], perf_counter_ns() - started)

        if order.time_in_force == TimeInForce.FOK and not self._can_fully_fill(order):
            reports.append(ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.EXPIRED, remaining_quantity=order.quantity, price=order.price, message="FOK could not fill", timestamp_ns=order.timestamp_ns))
            return MatchResult(reports, trades, [], perf_counter_ns() - started)

        reports.append(ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.ACCEPTED, remaining_quantity=order.remaining, price=order.price, message="accepted", timestamp_ns=order.timestamp_ns))
        self._match(order, trades)

        filled = order.quantity - order.remaining
        status = OrderStatus.FILLED if order.remaining == 0 and filled else OrderStatus.PARTIALLY_FILLED if filled else OrderStatus.ACCEPTED
        should_rest = order.remaining > 0 and order.order_type == OrderType.LIMIT and order.time_in_force == TimeInForce.GTC
        if should_rest:
            self._rest(order)
        elif order.remaining > 0 and order.time_in_force in {TimeInForce.IOC, TimeInForce.FOK}:
            status = OrderStatus.EXPIRED

        reports.append(ExecutionReport(order.order_id, order.client_id, order.symbol, status, filled_quantity=filled, remaining_quantity=order.remaining if order.order_id in self.order_index else 0, price=order.price, message="matched" if filled else "rested or expired", timestamp_ns=order.timestamp_ns))
        return MatchResult(reports, trades, [self._book_update(order.timestamp_ns)], perf_counter_ns() - started)

    def cancel(self, order_id: str, timestamp_ns: int) -> MatchResult:
        started = perf_counter_ns()
        order = self.order_index.pop(order_id, None)
        if not order:
            return MatchResult([ExecutionReport(order_id, "unknown", self.symbol, OrderStatus.REJECTED, message="order not found", timestamp_ns=timestamp_ns)], [], [], perf_counter_ns() - started)
        order.remaining = 0
        report = ExecutionReport(order.order_id, order.client_id, order.symbol, OrderStatus.CANCELLED, message="cancelled", timestamp_ns=timestamp_ns)
        return MatchResult([report], [], [self._book_update(timestamp_ns)], perf_counter_ns() - started)

    def replace(self, old_order_id: str, new_order: Order) -> MatchResult:
        cancel_result = self.cancel(old_order_id, new_order.timestamp_ns)
        if cancel_result.reports and cancel_result.reports[0].status == OrderStatus.REJECTED:
            return cancel_result
        submit_result = self.submit(new_order)
        reports = cancel_result.reports + submit_result.reports
        reports.append(ExecutionReport(new_order.order_id, new_order.client_id, new_order.symbol, OrderStatus.REPLACED, remaining_quantity=new_order.remaining, price=new_order.price, message=f"replaced {old_order_id}", timestamp_ns=new_order.timestamp_ns))
        return MatchResult(reports, submit_result.trades, cancel_result.market_data + submit_result.market_data, cancel_result.latency_ns + submit_result.latency_ns)

    def snapshot(self, depth: int = 5) -> BookSnapshot:
        return BookSnapshot(self.symbol, self._levels(self.bids, True, depth), self._levels(self.asks, False, depth), self.sequence)

    def _match(self, taker: Order, trades: List[Trade]) -> None:
        contra = self.asks if taker.side == Side.BUY else self.bids
        while taker.remaining > 0:
            best_price = self._best_price(contra, Side.SELL if taker.side == Side.BUY else Side.BUY)
            if best_price is None or not self._crosses(taker, best_price):
                break
            queue = contra[best_price]
            self._discard_dead(queue)
            if not queue:
                contra.pop(best_price, None)
                continue
            maker = queue[0]
            qty = min(taker.remaining, maker.remaining)
            taker.remaining -= qty
            maker.remaining -= qty
            trades.append(Trade(f"T-{uuid4().hex[:12]}", self.symbol, best_price, qty, taker.side, maker.order_id, taker.order_id, maker.client_id, taker.client_id, taker.timestamp_ns))
            if maker.remaining == 0:
                queue.popleft()
                self.order_index.pop(maker.order_id, None)
            if not queue:
                contra.pop(best_price, None)

    def _can_fully_fill(self, order: Order) -> bool:
        contra = self.asks if order.side == Side.BUY else self.bids
        needed = order.remaining
        for price in sorted(contra.keys(), reverse=(order.side == Side.SELL)):
            if not self._crosses(order, price):
                break
            needed -= sum(o.remaining for o in contra[price] if o.remaining > 0)
            if needed <= 0:
                return True
        return False

    def _would_cross(self, order: Order) -> bool:
        contra = self.asks if order.side == Side.BUY else self.bids
        best = self._best_price(contra, Side.SELL if order.side == Side.BUY else Side.BUY)
        return best is not None and self._crosses(order, best)

    def _rest(self, order: Order) -> None:
        book = self.bids if order.side == Side.BUY else self.asks
        assert order.price is not None
        was_empty = not book[order.price]
        book[order.price].append(order)
        self.order_index[order.order_id] = order
        if was_empty:
            heapq.heappush(self._bid_heap if order.side == Side.BUY else self._ask_heap, -order.price if order.side == Side.BUY else order.price)

    def _crosses(self, order: Order, best_price: int) -> bool:
        if order.order_type == OrderType.MARKET:
            return True
        assert order.price is not None
        return best_price <= order.price if order.side == Side.BUY else best_price >= order.price

    def _best_price(self, book: Dict[int, Deque[Order]], side: Side) -> Optional[int]:
        heap = self._ask_heap if side == Side.SELL else self._bid_heap
        while heap:
            price = heap[0] if side == Side.SELL else -heap[0]
            queue = book.get(price)
            if queue is not None:
                self._discard_dead(queue)
            if queue:
                return price
            if queue is not None and not queue:
                book.pop(price, None)
            heapq.heappop(heap)
        return None

    def _levels(self, book: Dict[int, Deque[Order]], reverse: bool, depth: int) -> List[BookLevel]:
        levels: List[BookLevel] = []
        for price in sorted(list(book.keys()), reverse=reverse):
            queue = book[price]
            self._discard_dead(queue)
            qty = sum(o.remaining for o in queue if o.remaining > 0)
            count = sum(1 for o in queue if o.remaining > 0)
            if qty:
                levels.append(BookLevel(price, qty, count))
            else:
                book.pop(price, None)
            if len(levels) >= depth:
                break
        return levels

    def _discard_dead(self, queue: Deque[Order]) -> None:
        while queue and queue[0].remaining <= 0:
            queue.popleft()

    def _book_update(self, timestamp_ns: int) -> MarketDataEvent:
        self.sequence += 1
        return MarketDataEvent(EventType.BOOK_UPDATE, self.symbol, self.sequence, timestamp_ns, self.snapshot(depth=5).to_dict())


class MatchingEngine:
    def __init__(self) -> None:
        self.books: Dict[str, LimitOrderBook] = {}

    def get_book(self, symbol: str) -> LimitOrderBook:
        if symbol not in self.books:
            self.books[symbol] = LimitOrderBook(symbol)
        return self.books[symbol]

    def submit(self, order: Order) -> MatchResult:
        return self.get_book(order.symbol).submit(order)

    def cancel(self, symbol: str, order_id: str, timestamp_ns: int) -> MatchResult:
        return self.get_book(symbol).cancel(order_id, timestamp_ns)

    def replace(self, symbol: str, old_order_id: str, new_order: Order) -> MatchResult:
        return self.get_book(symbol).replace(old_order_id, new_order)

    def snapshot(self, symbol: str, depth: int = 5) -> BookSnapshot:
        return self.get_book(symbol).snapshot(depth)
