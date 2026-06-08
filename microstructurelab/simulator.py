from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .analytics import book_imbalance, trade_summary
from .benchmark import percentile
from .gateway import OrderGateway
from .models import OrderRequest
from .scenarios import flow_from_config, flow_from_csv, market_maker_scenario, multi_symbol_flow, random_order_flow, volatility_shock_scenario


def run_flow(flow: Iterable[OrderRequest], scenario_name: str = "custom", primary_symbol: str = "AAPL") -> Dict[str, object]:
    gateway = OrderGateway()
    latencies: List[int] = []
    spreads: List[int] = []
    submitted = 0
    rejected = 0
    market_data_events = 0
    symbols_seen: set[str] = set()

    for request in flow:
        symbols_seen.add(request.symbol)
        submitted += 1
        result = gateway.submit(request)
        latencies.append(result.latency_ns)
        market_data_events += len(result.market_data)
        rejected += sum(1 for report in result.reports if report.status.value == "REJECTED")
        snapshot = gateway.matching_engine.snapshot(request.symbol)
        if snapshot.spread is not None:
            spreads.append(snapshot.spread)

    snapshot = gateway.matching_engine.snapshot(primary_symbol)
    mid = (snapshot.best_bid + snapshot.best_ask) / 200.0 if snapshot.best_bid and snapshot.best_ask else None
    return {
        "scenario": scenario_name,
        "submitted_orders": submitted,
        "trades": len(gateway.trades),
        "rejected_orders": rejected,
        "final_mid_price": mid,
        "benchmark": {
            "orders": submitted,
            "trades": len(gateway.trades),
            "p50_latency_ns": percentile(latencies, 50),
            "p95_latency_ns": percentile(latencies, 95),
            "p99_latency_ns": percentile(latencies, 99),
            "market_data_events": market_data_events,
            "avg_spread_ticks": sum(spreads) / len(spreads) if spreads else 0.0,
            "final_book_sequence": snapshot.sequence,
        },
        "analytics": {
            "trade_summary": trade_summary(gateway.trades),
            "symbols_seen": sorted(symbols_seen),
            "journal_events": len(gateway.journal.events),
            "book_imbalance": book_imbalance(snapshot),
            "risk": gateway.risk(),
        },
    }


def run_named_scenario(name: str, orders: int = 10_000) -> Dict[str, object]:
    if name == "market_maker":
        flow = market_maker_scenario(steps=orders)
    elif name == "random_flow":
        flow = random_order_flow(n=orders)
    elif name == "volatility_shock":
        flow = volatility_shock_scenario(steps=orders)
    elif name == "multi_symbol":
        flow = multi_symbol_flow(n=orders)
    else:
        raise ValueError(f"unknown scenario: {name}")
    return run_flow(flow, name)


def run_config(path: str) -> Dict[str, object]:
    return run_flow(flow_from_config(path), "config")


def run_replay(path: str) -> Dict[str, object]:
    return run_flow(flow_from_csv(path), "replay")
