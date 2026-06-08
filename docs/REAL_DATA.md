# Public-data screener

MicrostructureLab includes an optional watchlist screener. It can use deterministic sample data or public web data providers.

The screener is not an execution system. It does not place orders and does not connect to brokerage accounts.

## CLI

Sample mode:

```bash
python microstructurelab.py screen-open --symbols NVDA,TSLA,AMD,AAPL
```

Public data mode:

```bash
python microstructurelab.py screen-open --symbols NVDA,TSLA,AMD --market-provider yahoo --news-provider yahoo --community-provider reddit
```

## Signals

The screener combines:

- price gap versus previous close
- relative volume
- liquidity
- spread risk when available
- recent headlines
- community visibility
- risk flags

## Providers

- `sample`: deterministic offline data for tests and demos
- `yahoo`: public Yahoo endpoints for chart/headline data
- `gdelt`: GDELT document API for broad news search
- `reddit`: Reddit JSON search for community visibility

## Notes

Provider availability, rate limits, and data delays can vary. Treat this as a research and simulation input, not a recommendation engine.
