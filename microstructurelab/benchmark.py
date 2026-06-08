from __future__ import annotations

from time import perf_counter
from typing import Dict, List

from .gateway import OrderGateway
from .scenarios import random_order_flow


def percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    idx = min(len(values) - 1, int(round((pct / 100) * (len(values) - 1))))
    return values[idx]


def run_benchmark(orders: int = 100_000, symbol: str = "AAPL", seed: int = 7) -> Dict[str, float | int]:
    flow = random_order_flow(symbol=symbol, n=orders, seed=seed)
    gateway = OrderGateway()
    latencies: List[int] = []
    spreads: List[int] = []
    trade_count = 0
    rejected = 0
    market_data_events = 0
    started = perf_counter()
    for request in flow:
        result = gateway.submit(request)
        latencies.append(result.latency_ns)
        trade_count += len(result.trades)
        market_data_events += len(result.market_data)
        rejected += sum(1 for report in result.reports if report.status.value == "REJECTED")
        snapshot = gateway.matching_engine.snapshot(symbol)
        if snapshot.spread is not None:
            spreads.append(snapshot.spread)
    duration = perf_counter() - started
    submitted = len(flow)
    snapshot = gateway.matching_engine.snapshot(symbol)
    return {
        "orders": submitted,
        "trades": trade_count,
        "duration_sec": duration,
        "throughput_ops_sec": submitted / duration if duration else 0.0,
        "p50_latency_ns": percentile(latencies, 50),
        "p95_latency_ns": percentile(latencies, 95),
        "p99_latency_ns": percentile(latencies, 99),
        "rejected_orders": rejected,
        "market_data_events": market_data_events,
        "avg_spread_ticks": sum(spreads) / len(spreads) if spreads else 0.0,
        "final_book_sequence": snapshot.sequence,
    }
