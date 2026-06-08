from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, Optional

from .models import BookSnapshot, Trade


def vwap(trades: Iterable[Trade]) -> Optional[float]:
    trade_list = list(trades)
    qty = sum(trade.quantity for trade in trade_list)
    if qty == 0:
        return None
    return sum(trade.price * trade.quantity for trade in trade_list) / qty / 100.0


def book_imbalance(snapshot: BookSnapshot, depth: int = 5) -> Optional[float]:
    bid_qty = sum(level.quantity for level in snapshot.bids[:depth])
    ask_qty = sum(level.quantity for level in snapshot.asks[:depth])
    total = bid_qty + ask_qty
    if total == 0:
        return None
    return (bid_qty - ask_qty) / total


def spread_ticks(snapshot: BookSnapshot) -> Optional[int]:
    if snapshot.best_bid is None or snapshot.best_ask is None:
        return None
    return snapshot.best_ask - snapshot.best_bid


def trade_summary(trades: Iterable[Trade]) -> Dict[str, Any]:
    trade_list = list(trades)
    by_symbol: Dict[str, int] = {}
    notional_by_symbol: Dict[str, int] = {}
    for trade in trade_list:
        by_symbol[trade.symbol] = by_symbol.get(trade.symbol, 0) + trade.quantity
        notional_by_symbol[trade.symbol] = notional_by_symbol.get(trade.symbol, 0) + trade.notional
    return {
        "trade_count": len(trade_list),
        "total_quantity": sum(trade.quantity for trade in trade_list),
        "vwap": vwap(trade_list),
        "volume_by_symbol": by_symbol,
        "notional_by_symbol_dollars": {symbol: cents / 100.0 for symbol, cents in notional_by_symbol.items()},
    }


def snapshot_summary(snapshot: BookSnapshot) -> Dict[str, Any]:
    return {
        "symbol": snapshot.symbol,
        "sequence": snapshot.sequence,
        "best_bid": snapshot.best_bid,
        "best_ask": snapshot.best_ask,
        "spread_ticks": spread_ticks(snapshot),
        "mid_price": snapshot.mid_price / 100.0 if snapshot.mid_price is not None else None,
        "imbalance": book_imbalance(snapshot),
        "bids": [asdict(level) for level in snapshot.bids],
        "asks": [asdict(level) for level in snapshot.asks],
    }
