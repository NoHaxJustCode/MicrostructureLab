from __future__ import annotations

import csv
import json
import random
from itertools import count
from pathlib import Path
from typing import Dict, Iterable, List

from .models import OrderRequest, OrderType, Side, TimeInForce

_IDS = count(1)


def next_order_id(prefix: str = "O") -> str:
    return f"{prefix}-{next(_IDS)}"


def bootstrap_book(symbol: str = "AAPL", mid: int = 19_200, levels: int = 5, size: int = 500) -> List[OrderRequest]:
    orders: List[OrderRequest] = []
    for level in range(1, levels + 1):
        orders.append(OrderRequest(next_order_id("BID"), "maker-a", symbol, Side.BUY, OrderType.LIMIT, size, mid - level, TimeInForce.GTC))
        orders.append(OrderRequest(next_order_id("ASK"), "maker-b", symbol, Side.SELL, OrderType.LIMIT, size, mid + level, TimeInForce.GTC))
    return orders


def random_order_flow(symbol: str = "AAPL", n: int = 10_000, seed: int = 7, mid: int = 19_200) -> List[OrderRequest]:
    rng = random.Random(seed)
    flow = bootstrap_book(symbol=symbol, mid=mid)
    for _ in range(n):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        is_market = rng.random() < 0.12
        qty = rng.choice([10, 25, 50, 100, 200, 500])
        if is_market:
            flow.append(OrderRequest(next_order_id("MKT"), rng.choice(["alpha", "beta", "gamma"]), symbol, side, OrderType.MARKET, qty, None, TimeInForce.IOC))
        else:
            price = mid + rng.randint(-8, 8)
            tif = TimeInForce.IOC if rng.random() < 0.08 else TimeInForce.GTC
            post_only = rng.random() < 0.05
            flow.append(OrderRequest(next_order_id("LMT"), rng.choice(["alpha", "beta", "gamma"]), symbol, side, OrderType.LIMIT, qty, price, tif, post_only))
    return flow


def market_maker_scenario(symbol: str = "AAPL", steps: int = 2_000, seed: int = 42) -> List[OrderRequest]:
    rng = random.Random(seed)
    mid = 19_200
    flow = bootstrap_book(symbol=symbol, mid=mid, levels=3, size=800)
    for _ in range(steps):
        if rng.random() < 0.35:
            flow.append(OrderRequest(next_order_id("MMB"), "market-maker", symbol, Side.BUY, OrderType.LIMIT, 100, mid - 1, TimeInForce.GTC, True))
            flow.append(OrderRequest(next_order_id("MMA"), "market-maker", symbol, Side.SELL, OrderType.LIMIT, 100, mid + 1, TimeInForce.GTC, True))
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        flow.append(OrderRequest(next_order_id("TAKER"), "taker", symbol, side, OrderType.MARKET, rng.choice([25, 50, 100]), None, TimeInForce.IOC))
        if rng.random() < 0.05:
            mid += rng.choice([-1, 1])
    return flow


def volatility_shock_scenario(symbol: str = "AAPL", steps: int = 2_000, seed: int = 99) -> List[OrderRequest]:
    rng = random.Random(seed)
    mid = 19_200
    flow = bootstrap_book(symbol, mid, levels=8, size=600)
    for i in range(steps):
        if i == steps // 3:
            mid -= 80
        if i == (2 * steps) // 3:
            mid += 130
        side = Side.BUY if rng.random() < 0.48 else Side.SELL
        qty = rng.choice([50, 100, 250, 500, 1000])
        if rng.random() < 0.22:
            flow.append(OrderRequest(next_order_id("SHOCK"), "shock-taker", symbol, side, OrderType.MARKET, qty, None, TimeInForce.IOC))
        else:
            flow.append(OrderRequest(next_order_id("VOL"), rng.choice(["alpha", "beta", "gamma", "hedger"]), symbol, side, OrderType.LIMIT, qty, mid + rng.randint(-12, 12), TimeInForce.GTC))
    return flow


def multi_symbol_flow(symbols: Dict[str, int] | None = None, n: int = 5_000, seed: int = 11) -> List[OrderRequest]:
    symbols = symbols or {"AAPL": 19_200, "MSFT": 42_500, "NVDA": 91_000}
    flow: List[OrderRequest] = []
    for symbol, mid in symbols.items():
        flow.extend(bootstrap_book(symbol, mid, levels=4, size=800))
    rng = random.Random(seed)
    symbol_list = list(symbols.items())
    for _ in range(n):
        symbol, mid = rng.choice(symbol_list)
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        order_type = OrderType.MARKET if rng.random() < 0.1 else OrderType.LIMIT
        tif = TimeInForce.IOC if order_type == OrderType.MARKET else TimeInForce.GTC
        price = None if order_type == OrderType.MARKET else mid + rng.randint(-8, 8)
        flow.append(OrderRequest(next_order_id("MS"), rng.choice(["alpha", "beta", "gamma", "cross-asset"]), symbol, side, order_type, rng.choice([10, 50, 100, 500]), price, tif))
    return flow


def flow_from_config(path: str | Path) -> List[OrderRequest]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    name = config.get("scenario", "random_flow")
    orders = int(config.get("orders", 10_000))
    symbol = config.get("symbol", "AAPL")
    seed = int(config.get("seed", 7))
    mid = int(config.get("mid", 19_200))
    if name == "random_flow":
        return random_order_flow(symbol=symbol, n=orders, seed=seed, mid=mid)
    if name == "market_maker":
        return market_maker_scenario(symbol=symbol, steps=orders, seed=seed)
    if name == "volatility_shock":
        return volatility_shock_scenario(symbol=symbol, steps=orders, seed=seed)
    if name == "multi_symbol":
        return multi_symbol_flow(n=orders, seed=seed)
    raise ValueError(f"unknown scenario: {name}")


def flow_from_csv(path: str | Path) -> List[OrderRequest]:
    orders: List[OrderRequest] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            order_type = OrderType[row["order_type"].upper()]
            price = int(row["price"]) if row.get("price") else None
            orders.append(OrderRequest(row["order_id"], row["client_id"], row["symbol"], Side[row["side"].upper()], order_type, int(row["quantity"]), price, TimeInForce[row.get("time_in_force", "GTC").upper()]))
    return orders
