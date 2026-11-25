PYTHON := .venv/bin/python

.PHONY: setup test datasets train research evaluate
setup:
	bash scripts/setup.sh
test:
	$(PYTHON) -m pytest -q
datasets:
	$(PYTHON) scripts/download_datasets.py
	$(PYTHON) scripts/preprocess_all.py
train:
	$(PYTHON) scripts/train_all.py
research:
	$(PYTHON) scripts/run_research.py
evaluate:
	$(PYTHON) scripts/evaluate_all.py
