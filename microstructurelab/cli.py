from __future__ import annotations

import argparse
import json
from pprint import pprint

from .benchmark import run_benchmark
from .realdata import screen_open
from .simulator import run_config, run_named_scenario, run_replay


def _print(value, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str))
    else:
        pprint(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="microstructurelab")
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("benchmark")
    bench.add_argument("--orders", type=int, default=100000)
    bench.add_argument("--symbol", default="AAPL")
    bench.add_argument("--json", action="store_true")

    sim = sub.add_parser("run-sim")
    sim.add_argument("--scenario", default="market_maker")
    sim.add_argument("--orders", type=int, default=2000)
    sim.add_argument("--json", action="store_true")

    replay = sub.add_parser("replay")
    replay.add_argument("--file", required=True)
    replay.add_argument("--json", action="store_true")

    config = sub.add_parser("run-config")
    config.add_argument("--file", required=True)
    config.add_argument("--json", action="store_true")

    screen = sub.add_parser("screen-open")
    screen.add_argument("--symbols", required=True)
    screen.add_argument("--market-provider", default="sample")
    screen.add_argument("--news-provider", default="sample")
    screen.add_argument("--community-provider", default="sample")
    screen.add_argument("--json", action="store_true")

    sub.add_parser("serve")
    args = parser.parse_args()

    if args.command == "benchmark":
        _print(run_benchmark(args.orders, args.symbol), args.json)
    elif args.command == "run-sim":
        _print(run_named_scenario(args.scenario, args.orders), args.json)
    elif args.command == "replay":
        _print(run_replay(args.file), args.json)
    elif args.command == "run-config":
        _print(run_config(args.file), args.json)
    elif args.command == "screen-open":
        symbols = [symbol.strip() for symbol in args.symbols.split(",")]
        _print([row.to_dict() for row in screen_open(symbols, args.market_provider, args.news_provider, args.community_provider)], args.json)
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("microstructurelab.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
