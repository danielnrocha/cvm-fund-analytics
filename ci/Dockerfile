FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
ENV DBT_SEND_ANONYMOUS_USAGE_STATS=false PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY compatibility/dbt-v2-metricflow/requirements-*.lock /tmp/locks/
RUN python -m venv /opt/venv-dbt && /opt/venv-dbt/bin/pip install --no-cache-dir -r /tmp/locks/requirements-dbt.lock && python -m venv /opt/venv-mf && /opt/venv-mf/bin/pip install --no-cache-dir -r /tmp/locks/requirements-mf.lock
COPY . /workspace/
RUN ln -s /opt/venv-dbt compatibility/dbt-v2-metricflow/.venv-dbt && ln -s /opt/venv-mf compatibility/dbt-v2-metricflow/.venv-mf

RUN /opt/venv-mf/bin/python ci/docs.py --bootstrap

ENV ADBC_DRIVER_PATH=/workspace/ci/drivers
