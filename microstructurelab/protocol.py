from __future__ import annotations

from typing import Union

from .models import CancelRequest, ExecutionReport, OrderRequest, OrderStatus, OrderType, ReplaceRequest, Side, TimeInForce

_SIDE_FIX = {"1": Side.BUY, "2": Side.SELL, "BUY": Side.BUY, "SELL": Side.SELL}
_TYPE_FIX = {"1": OrderType.MARKET, "2": OrderType.LIMIT, "MARKET": OrderType.MARKET, "LIMIT": OrderType.LIMIT}
_TIF_FIX = {"0": TimeInForce.GTC, "3": TimeInForce.IOC, "4": TimeInForce.FOK, "GTC": TimeInForce.GTC, "IOC": TimeInForce.IOC, "FOK": TimeInForce.FOK}

FixRequest = Union[OrderRequest, CancelRequest, ReplaceRequest]


def parse_fix_like(message: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in message.strip().replace("\x01", "|").split("|"):
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"invalid field: {part}")
        key, value = part.split("=", 1)
        fields[key] = value
    return fields


def order_from_fix_like(message: str) -> OrderRequest:
    fields = parse_fix_like(message)
    if fields.get("35") != "D":
        raise ValueError("expected 35=D")
    order_type = _TYPE_FIX[fields.get("40", "2").upper()]
    price = int(fields["44"]) if order_type == OrderType.LIMIT and "44" in fields else None
    return OrderRequest(fields["11"], fields.get("49", "client-default"), fields["55"], _SIDE_FIX[fields["54"].upper()], order_type, int(fields["38"]), price, _TIF_FIX.get(fields.get("59", "0").upper(), TimeInForce.GTC), fields.get("18", "") == "6" or fields.get("PO", "N").upper() == "Y")


def request_from_fix_like(message: str) -> FixRequest:
    fields = parse_fix_like(message)
    msg_type = fields.get("35")
    if msg_type == "D":
        return order_from_fix_like(message)
    if msg_type == "F":
        return CancelRequest(fields["41"], fields.get("49", "client-default"), fields["55"])
    if msg_type == "G":
        return ReplaceRequest(fields["41"], fields["11"], fields.get("49", "client-default"), fields["55"], int(fields["38"]), int(fields["44"]), _TIF_FIX.get(fields.get("59", "0").upper(), TimeInForce.GTC), fields.get("18", "") == "6" or fields.get("PO", "N").upper() == "Y")
    raise ValueError(f"unsupported message type: {msg_type}")


def execution_report_to_fix_like(report: ExecutionReport) -> str:
    status_code = {
        OrderStatus.ACCEPTED: "0",
        OrderStatus.PARTIALLY_FILLED: "1",
        OrderStatus.FILLED: "2",
        OrderStatus.CANCELLED: "4",
        OrderStatus.REPLACED: "5",
        OrderStatus.REJECTED: "8",
        OrderStatus.EXPIRED: "C",
    }[report.status]
    fields = {"35": "8", "11": report.order_id, "49": "MicrostructureLab", "56": report.client_id, "55": report.symbol, "39": status_code, "14": str(report.filled_quantity), "151": str(report.remaining_quantity), "58": report.message}
    return "|".join(f"{k}={v}" for k, v in fields.items()) + "|"
