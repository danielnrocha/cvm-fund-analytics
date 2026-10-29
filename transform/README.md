# CVM local: ingestão → dbt v2 → MetricFlow

A vertical usa arquivos CVM congelados, landing imutável e sources físicos com envelopes JSON. Não utiliza dbt seeds. População: 60 classes, abril–setembro/2026. [Design e limitações da ingestão](../specs/ingestion.md).

Com os dois ambientes do [probe](../compatibility/dbt-v2-metricflow/README.md) instalados, executar da raiz:

```sh
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/ingest_cvm.py
cd transform
../compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt build --profiles-dir .
../compatibility/dbt-v2-metricflow/.venv-mf/bin/mf validate-configs
../compatibility/dbt-v2-metricflow/.venv-mf/bin/mf query --metrics reported_net_assets_eop,net_flow,reporting_coverage_period,reporting_coverage_eop --group-by metric_time__month
```

`scripts/prepare_frozen_cvm.py` permanece como alias de compatibilidade para a ingestão, sem gerar seeds. Os ZIPs em `profiling/cvm/raw/` precisam corresponder ao manifest: não se baixa uma nova versão para substituir hashes silenciosamente. Preservar os bytes congelados para o ensaio; URLs oficiais são mutáveis. Atribuição e licença CVM/ODbL permanecem nos manifests e na documentação de profiling.

`CVM_DB_PATH` escolhe um banco isolado. Um único writer por banco. O writer Python fixa armazenamento compatível com o engine dbt. As tabelas `landing.*` são carregadas em transação; arquivos content-addressed ficam em `data/landing/objects/` e não são sobrescritos. Quarentena em `main.quarantine` inclui payload e motivo. `main.audit_ingestion_files` mostra aceitos, rejeitados e excluídos por arquivo.

A classificação e calendário são contratos congelados; um registro em data não prevista bloqueia o build. PL/fluxo/cobertura mantêm os oráculos anteriores. Fluxo sem cobertura pode induzir interpretação errada: apresentar os dois. Último disponível por entidade, cotistas, retornos e carteira continuam fora desta publicação.

**Aceite requer `dbt build`**: `run` ignora gates. Um build não é promoção atômica; intermediários podem mudar quando a publicação falha. `--full-refresh` só pode reconstruir histórico completo quando recebe todas as capturas retidas. Não usar automaticamente com delta.

Testes, da raiz:

```sh
compatibility/dbt-v2-metricflow/.venv-mf/bin/python -m unittest discover -s tests/ingestion -v
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/check_ingestion.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/check_rejections.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/check_history.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/check_real_oracles.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python scripts/check_semantics.py
```

Os testes de integração usam bancos temporários. Fixtures sintéticas são adaptadas para sources por `tests/ingestion/fixture_loader.py`; arquivos CSV temporários desses testes não são recursos dbt. O teste clean pode atualizar `target/` com seu manifesto temporário; antes de usar o MetricFlow no banco principal, rode novamente o build principal. Tasks do VS Code incluem ingestão e build.

## Publicação local

Consulte [snapshots](../specs/snapshot-publication.md) para build isolado, promoção com expectativa da versão corrente, leitura read-only e rollback. Não sirva este banco de trabalho como publicação: use `scripts/snapshot.py` a partir da raiz e os bundles em `data/releases`.

## CI e gate semântico UAT

[Operação e contrato](../specs/ci-uat.md). `scripts/snapshot.py compare` gera um relatório vinculado a baseline/candidato; promoção UAT exige `--gate` e `--expected`. Linux é executado via `ci/Dockerfile` e `ci/run.py`, com bootstrap online e aceite offline.

## Project navigation and style

- `models/staging/cvm`: source metadata, JSON classification and typed observations.
- `models/reference`: frozen cohort/calendar, captures and the semantic time spine.
- `models/intermediate`: identity resolution, duplicate aggregation and latest capture selection.
- `models/history`: append-only report versions; not a claim of a complete Data Vault framework.
- `models/marts`: daily fact contract and MetricFlow definitions.
- `models/audit`: quarantine and file reconciliation.

Names and output schemas remain stable across folder moves. Unit fixtures spanning multiple models stay in `models/intermediate/unit_tests.yml`. Run `make lint format-check` from the repository root. See [contributor conventions](../CONTRIBUTING.md) and [refactor evidence](../specs/repository-review.md).
