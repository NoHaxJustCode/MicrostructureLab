from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        return 1 if self == Side.BUY else -1


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    REPLACED = "REPLACED"
    EXPIRED = "EXPIRED"


class EventType(str, Enum):
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    TRADE = "TRADE"
    BOOK_UPDATE = "BOOK_UPDATE"
    CANCELLED = "CANCELLED"
    REPLACED = "REPLACED"
    RISK_REJECTED = "RISK_REJECTED"


@dataclass(slots=True)
class Order:
    order_id: str
    client_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: int
    price: Optional[int] = None
    timestamp_ns: int = 0
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = False
    remaining: int = field(init=False)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("limit orders require a price")
        if self.price is not None and self.price <= 0:
            raise ValueError("price must be positive")
        self.remaining = self.quantity


@dataclass(slots=True)
class OrderRequest:
    order_id: str
    client_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: int
    price: Optional[int] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = False

    def to_order(self, timestamp_ns: int) -> Order:
        return Order(
            order_id=self.order_id,
            client_id=self.client_id,
            symbol=self.symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=self.quantity,
            price=self.price,
            time_in_force=self.time_in_force,
            post_only=self.post_only,
            timestamp_ns=timestamp_ns,
        )


@dataclass(slots=True)
class CancelRequest:
    order_id: str
    client_id: str
    symbol: str


@dataclass(slots=True)
class ReplaceRequest:
    order_id: str
    new_order_id: str
    client_id: str
    symbol: str
    quantity: int
    price: int
    time_in_force: TimeInForce = TimeInForce.GTC
    post_only: bool = False


@dataclass(slots=True)
class Trade:
    trade_id: str
    symbol: str
    price: int
    quantity: int
    aggressor_side: Side
    maker_order_id: str
    taker_order_id: str
    maker_client_id: str
    taker_client_id: str
    timestamp_ns: int

    @property
    def notional(self) -> int:
        return self.price * self.quantity


@dataclass(slots=True)
class ExecutionReport:
    order_id: str
    client_id: str
    symbol: str
    status: OrderStatus
    filled_quantity: int = 0
    remaining_quantity: int = 0
    price: Optional[int] = None
    message: str = ""
    timestamp_ns: int = 0


@dataclass(slots=True)
class BookLevel:
    price: int
    quantity: int
    order_count: int


@dataclass(slots=True)
class BookSnapshot:
    symbol: str
    bids: List[BookLevel]
    asks: List[BookLevel]
    sequence: int

    @property
    def best_bid(self) -> Optional[int]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[int]:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[int]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sequence": self.sequence,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "mid_price": self.mid_price,
            "bids": [asdict(level) for level in self.bids],
            "asks": [asdict(level) for level in self.asks],
        }


@dataclass(slots=True)
class MarketDataEvent:
    event_type: EventType
    symbol: str
    sequence: int
    timestamp_ns: int
    payload: Dict[str, Any]


@dataclass(slots=True)
class JournalEvent:
    sequence: int
    timestamp_ns: int
    event_type: str
    symbol: str
    payload: Dict[str, Any]


@dataclass(slots=True)
class MatchResult:
    reports: List[ExecutionReport]
    trades: List[Trade]
    market_data: List[MarketDataEvent]
    latency_ns: int
