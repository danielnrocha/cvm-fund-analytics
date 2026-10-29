SHELL := /bin/sh
COMPAT := compatibility/dbt-v2-metricflow
PY := $(COMPAT)/.venv-mf/bin/python
DBT := $(abspath $(COMPAT)/.venv-dbt/bin/dbt)
MF := $(abspath $(COMPAT)/.venv-mf/bin/mf)
export DBT_SEND_ANONYMOUS_USAGE_STATS := false

.PHONY: setup fetch test build metrics docs
setup:
	uv venv --python 3.12 $(COMPAT)/.venv-dbt
	uv pip install --python $(COMPAT)/.venv-dbt/bin/python -r $(COMPAT)/requirements-dbt.lock
	uv venv --python 3.12 $(COMPAT)/.venv-mf
	uv pip install --python $(PY) -r $(COMPAT)/requirements-mf.lock
fetch:
	$(PY) ci/fetch_inputs.py

test:
	@set -e; for group in business ingestion release ci demo; do $(PY) -m unittest discover -s tests/$$group -v; done

build: fetch
	$(PY) scripts/ingest_cvm.py
	cd transform && $(DBT) build --profiles-dir . --static-analysis strict --generate-info-schema
	$(PY) scripts/check_real_oracles.py

metrics:
	cd transform && $(MF) validate-configs
	$(PY) scripts/check_semantics.py

docs:
	$(PY) $(COMPAT)/pinned_docs.py --project transform

.PHONY: demo-prepare demo-reset
demo-prepare:
	$(PY) demo/workspace.py prepare
demo-reset:
	$(PY) demo/workspace.py reset

.PHONY: lint format-check format
lint:
	cd transform && $(DBT) lint --profiles-dir . --no-version-check
format-check:
	cd transform && $(DBT) format --check --profiles-dir . --no-version-check
format:
	cd transform && $(DBT) format --profiles-dir . --no-version-check
