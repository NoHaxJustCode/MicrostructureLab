from microstructurelab.benchmark import run_benchmark
from microstructurelab.simulator import run_named_scenario


def test_benchmark_shape():
    result = run_benchmark(orders=20)
    assert result["orders"] >= 20
    assert "p99_latency_ns" in result


def test_market_maker_scenario_runs():
    result = run_named_scenario("market_maker", orders=20)
    assert result["submitted_orders"] >= 20
    assert "analytics" in result
