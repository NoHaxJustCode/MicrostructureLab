# Benchmarking

Run:

```bash
python microstructurelab.py benchmark --orders 100000
```

The benchmark sends generated order flow through the full path:

```text
request -> gateway -> risk -> matching engine -> journal -> analytics
```

Reported metrics include:

- submitted order count
- generated trade count
- throughput
- p50/p95/p99 latency
- rejected requests
- book update count
- average spread in ticks
- final sequence number

Benchmark values vary by machine and Python runtime. Use them for local comparisons between implementation changes.
