from microstructurelab.realdata import screen_open


def test_sample_screener_orders_candidates():
    rows = screen_open(["NVDA", "AAPL"], "sample", "sample", "sample")
    assert rows
    assert rows[0].score >= rows[-1].score
    assert rows[0].symbol in {"NVDA", "AAPL"}
