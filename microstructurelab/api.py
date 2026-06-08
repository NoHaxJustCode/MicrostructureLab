from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .benchmark import run_benchmark
from .gateway import OrderGateway
from .models import OrderRequest, OrderType, Side, TimeInForce
from .realdata import screen_open
from .simulator import run_named_scenario

app = FastAPI(title="MicrostructureLab", version="1.1.0")
gateway = OrderGateway()


class ApiOrder(BaseModel):
    order_id: str
    client_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    price: int | None = None
    time_in_force: str = "GTC"
    post_only: bool = False


class ScreenRequest(BaseModel):
    symbols: List[str]
    market_provider: str = "sample"
    news_provider: str = "sample"
    community_provider: str = "sample"


@app.get("/", response_class=HTMLResponse)
def index():
    path = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "<h1>MicrostructureLab</h1>"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders")
def submit_order(order: ApiOrder):
    request = OrderRequest(order.order_id, order.client_id, order.symbol, Side[order.side.upper()], OrderType[order.order_type.upper()], order.quantity, order.price, TimeInForce[order.time_in_force.upper()], order.post_only)
    result = gateway.submit(request)
    return {"reports": [asdict(report) for report in result.reports], "trades": [asdict(trade) for trade in result.trades], "latency_ns": result.latency_ns}


@app.get("/book/{symbol}")
def book(symbol: str):
    return gateway.matching_engine.snapshot(symbol.upper()).to_dict()


@app.get("/analytics")
def analytics():
    return {"trades": len(gateway.trades), "positions": gateway.positions(), "risk": gateway.risk()}


@app.get("/journal")
def journal(limit: int = 100):
    return gateway.journal.tail(limit)


@app.get("/risk")
def risk():
    return gateway.risk()


@app.get("/benchmark")
def benchmark(orders: int = 10000, symbol: str = "AAPL"):
    return run_benchmark(orders, symbol)


@app.get("/scenario/{name}")
def scenario(name: str, orders: int = 2000):
    return run_named_scenario(name, orders)


@app.post("/screen/open")
def screen(req: ScreenRequest):
    return [row.to_dict() for row in screen_open(req.symbols, req.market_provider, req.news_provider, req.community_provider)]
