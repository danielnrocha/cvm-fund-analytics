# Gates finais de compatibilidade — 28/10/2026

**Resultado: os quatro gates solicitados passaram na fixture isolada em macOS arm64.** Stack permanece dbt v2 2.0.9 + DuckDB + MetricFlow local. Nenhum modelo do projeto de negócio foi implementado.

[Evidências estruturadas](../compatibility/dbt-v2-metricflow/evidence/remaining-gates-results.json), [resumo da execução](../compatibility/dbt-v2-metricflow/evidence/remaining-gates-summary.log) e [runner reproduzível](../compatibility/dbt-v2-metricflow/run_remaining_gates.py).

## Unit test nativo

`dbt test --select test_type:unit` executou a fixture declarada em `models/unit_probe.yml` sobre `stg_external_json`. Entradas mockadas por `source()` incluem JSON válido, número inválido e JSON malformado.

- Verde: saída correta aprovada.
- Vermelho: mutação real do SQL, `invalid_revenue` → `wrong_reason`, reprovada com diff de resultados; não foi falha de YAML/instalação.
- Verde após restauração: teste aprovado novamente; modelo terminou sem a mutação.

Não usamos `compute: local` nem seu flag experimental. Com adapter DuckDB, o compute padrão já é o banco local. A funcionalidade experimental de execução local de SQL de outros warehouses é outra capacidade.

Evidência: [falha esperada](../compatibility/dbt-v2-metricflow/evidence/37-unit-red.log) e [restauração](../compatibility/dbt-v2-metricflow/evidence/38-unit-green-restored.log). O renderizador do diff exibiu `[unsupported]` para o contador de tags, mas o teste verde passou; não usar esse renderer como representação canônica dos valores.

## Contrato de modelo

`contract_probe` é uma tabela mínima com `contract.enforced: true`, `shipment_id INTEGER` e `profit DECIMAL(18,2)`.

- Contrato correto: build aprovado.
- Tipo VARCHAR no lugar de DECIMAL: bloqueado por `data type mismatch`.
- `renamed_profit` no lugar de `profit`: bloqueado por coluna ausente na definição e ausente no contrato.
- Restauração: build aprovado.

[Erro de tipo](../compatibility/dbt-v2-metricflow/evidence/40-contract-red-type.log), [erro de nome](../compatibility/dbt-v2-metricflow/evidence/40-contract-red-missing.log). O erro vem do contrato enforced, não apenas de warning do analisador estático. A prova cobre nomes e tipos de tabela; não comprova enforcement de PK/FK/NOT NULL, precisão incompatível, contratos de incremental ou versionamento de modelos. Esses comportamentos só devem ser prometidos após testes próprios quando necessários.

## Semiaditividade executada no MetricFlow

Fixture sintética com duas contas e oito observações em janeiro/fevereiro. Grão: conta × data; identificador primário distinto por observação, conta como entidade estrangeira. Não declarar conta como primary numa tabela diária.

Configuração nova validada:

```yaml
non_additive_dimension:
  name: balance_date
  window_agg: max
  group_by: []       # última data observada na população consultada
```

A segunda métrica usa `group_by: [account]`, escolhendo a última observação de cada conta. Os nomes antigos `window_choice`/`window_groupings` não são a sintaxe de autoria usada nesta versão.

| Consulta | Última data observada | Última observação por conta |
|---|---:|---:|
| Janeiro | 110 | 330 |
| Fevereiro | 390 | 390 |
| Todo o período | 390 | 390 |
| Janeiro, conta A (agrupada) | 110 | 110 |
| Janeiro, conta B (agrupada) | null | 220 |
| Dia sem observação, 15/01 | null | null |

Queries de grão diário, mensal, total, filtro temporal e agrupamento por conta foram verificadas com oráculos explícitos. Sem preenchimento automático de missing por zero.

O teste também removeu temporariamente `non_additive_dimension`, regenerou o manifesto com v2 e executou a query: o resultado incorreto foi **1.380**, contra **390** no oráculo. Restaurada a configuração, o resultado voltou a 390. Isso comprova que a verificação detecta uma regressão de semântica que ainda compila e executa.

Limite importante: `max` escolhe uma data **observada**, não garante fechamento oficial de calendário, completude da coorte ou limite de defasagem. O valor 110 em janeiro tem cobertura parcial; não equivale ao patrimônio completo da coorte. `reported_net_assets_eop` do projeto real continuará exigindo data de corte explícita, elegibilidade e cobertura. A métrica latest-available exige datas e staleness por entidade. A soma de snapshots mensais não pode substituir o total de saldo no período.

## Driver de documentação fixado e sem fallback silencioso

[Lock canônico](../compatibility/dbt-v2-metricflow/docs-driver.lock.json) e [wrapper](../compatibility/dbt-v2-metricflow/pinned_docs.py):

- dbt: **2.0.9**.
- Driver auxiliar: **duckdb_extended 0.21.0.dev+dbt0.0.31**.
- Plataforma validada: **Darwin-arm64**.
- Entrypoint: `duckdb_adbc_init`.
- Tamanho: **72.060.224 bytes**.
- SHA-256: `4de5870f4da9a141993369f11b92affae48eb7f6dd6d3e8d94e378cba1bf47d4`.

O wrapper confere plataforma, versão do dbt, tamanho e hash, cria manifesto ADBC local e define `ADBC_DRIVER_PATH` apenas para a geração de docs. Não troca o driver de transformação nem o DuckDB Python do MetricFlow. Driver ausente ou divergente causa erro; não aceita automaticamente bytes novos.

A documentação foi gerada com rede e leitura do cache global de drivers bloqueadas, comprovando uso da cópia fixada. Um arquivo corrompido foi rejeitado pelo verificador. Evidência: [rejeição](../compatibility/dbt-v2-metricflow/evidence/49-corrupt-driver-rejected.log) e [docs isoladas](../compatibility/dbt-v2-metricflow/evidence/50-pinned-docs.log).

Bootstrap: `pinned_docs.py --bootstrap` usa o download oficial feito pelo dbt 2.0.9 e só prepara o arquivo se corresponder ao lock. `--prepare` copia uma instalação já disponível no cache, após verificar hash. A execução normal não baixa nada. O hash fixa o artefato observado; não é apresentado como assinatura criptográfica do fornecedor. Binários ficam em `drivers/`, fora do Git.

Linux/Windows precisam de locks próprios, obtidos e testados nas respectivas plataformas. O wrapper recusa plataforma não homologada; não fingimos que o hash Darwin garante CI Linux. Esse trabalho é uma condição da entrega de CI, não uma pendência de compatibilidade do laptop da demo.

## Como reproduzir

Na pasta `compatibility/dbt-v2-metricflow`, após instalar os locks Python e preparar a fixture:

```sh
.venv-mf/bin/python load_json_fixture.py
.venv-mf/bin/python pinned_docs.py --bootstrap
.venv-mf/bin/python run_remaining_gates.py
.venv-mf/bin/python run_probe.py
.venv-mf/bin/python verify_extended.py
```

O bootstrap precisa de internet se o cache estiver vazio; as execuções de teste usam bloqueio de rede. O wrapper docs aplica seu próprio sandbox, incluindo bloqueio de cache, e não deve ser envolvido em outro `sandbox-exec` (macOS rejeita o sandbox aninhado). Os runners tratam essa diferença explicitamente.

Fontes primárias: [unit tests](https://docs.getdbt.com/docs/build/unit-tests), [model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts), [migração do YAML semântico](https://docs.getdbt.com/docs/build/latest-metrics-spec) e [manifestos ADBC](https://arrow.apache.org/adbc/current/format/driver_manifests.html). A evidência executável tem precedência sobre inferências a partir desses textos.
