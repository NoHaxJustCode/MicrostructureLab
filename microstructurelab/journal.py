from __future__ import annotations

import json
from dataclasses import asdict
from time import time_ns
from typing import Any, Dict, Iterable, List

from .models import ExecutionReport, JournalEvent, MarketDataEvent, Trade


class EventJournal:
    def __init__(self) -> None:
        self._events: List[JournalEvent] = []
        self._sequence = 0

    def append(self, event_type: str, symbol: str, payload: Dict[str, Any], timestamp_ns: int | None = None) -> JournalEvent:
        self._sequence += 1
        event = JournalEvent(self._sequence, timestamp_ns or time_ns(), event_type, symbol, payload)
        self._events.append(event)
        return event

    def record_reports(self, reports: Iterable[ExecutionReport]) -> None:
        for report in reports:
            self.append("execution_report", report.symbol, asdict(report), report.timestamp_ns)

    def record_trades(self, trades: Iterable[Trade]) -> None:
        for trade in trades:
            self.append("trade", trade.symbol, asdict(trade), trade.timestamp_ns)

    def record_market_data(self, events: Iterable[MarketDataEvent]) -> None:
        for event in events:
            self.append(event.event_type.value.lower(), event.symbol, asdict(event), event.timestamp_ns)

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [asdict(event) for event in self._events[-limit:]]

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(event), default=str) for event in self._events)

    @property
    def events(self) -> List[JournalEvent]:
        return list(self._events)
