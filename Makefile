.PHONY: install test serve

install:
	python -m pip install -r requirements.txt

test:
	pytest -q

serve:
	uvicorn microstructurelab.api:app --reload
