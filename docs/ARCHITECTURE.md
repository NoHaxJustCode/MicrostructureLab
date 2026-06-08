# Architecture

MicrostructureLab is organized around a compact exchange-style event pipeline.

```text
CLI / API / Dashboard
        |
        v
Gateway
        |
        v
Risk checks
        |
        v
Matching engine
        |
        +--> Reports
        +--> Trades
        +--> Book updates
        |
        v
Journal / Analytics / Benchmarks
```

## Matching engine

The matching engine keeps one limit order book per symbol. Each book uses FIFO queues per price level and heap-backed best-price lookup for bids and asks.

Supported behavior:

- limit and market orders
- IOC and FOK handling
- post-only checks
- cancel and replace
- partial fills
- sequence-numbered book updates

## Gateway and risk

The gateway applies checks before forwarding accepted requests to the book. The risk layer handles quantity limits, notional limits, price-deviation checks, projected position limits, client throttles, and kill switches.

## Journal

Reports, trades, and book updates are written to an append-only in-memory event journal. The journal gives the dashboard and analytics layer a consistent event stream to inspect.
