PY := python3

.PHONY: install lint test data dashboard clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"

lint:
	ruff check src tests

test:
	pytest -q

data:
	$(PY) scripts/generate_sample_data.py

dashboard:
	streamlit run app/dashboard.py

clean:
	rm -rf .pytest_cache .ruff_cache data/synthesized reports/*.csv
