# MicrostructureLab

MicrostructureLab is a Python simulator for order-book systems, event replay, benchmarks, and dashboard-based experimentation.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python microstructurelab.py benchmark --orders 100000
python microstructurelab.py serve
```

## Contents

- `microstructurelab/`: core package
- `tests/`: test suite
- `frontend/`: local dashboard
- `examples/`: sample replay/config files
- `docs/`: design notes

## Roadmap

See `TODO.md`.
