# Pesquisa delimitada: dados reais CVM

Scripts de profiling, não pipeline de produção. Executar a partir da raiz do workspace:

```sh
compatibility/dbt-v2-metricflow/.venv-mf/bin/python profiling/cvm/download.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python profiling/cvm/profile.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python profiling/cvm/cohort.py
compatibility/dbt-v2-metricflow/.venv-mf/bin/python profiling/cvm/validate.py
```

Requer Python e DuckDB do ambiente já fixado no probe. Download usa biblioteca padrão, até três requisições simultâneas e limite por arquivo. `raw/`, `extracted/` e banco DuckDB são descartáveis/ignorados. Os originais são Latin-1; conversões UTF-8 são derivadas locais.

`evidence/sources.json` fixa a captura. Reexecução verifica hashes, preserva timestamps existentes e recusa bytes diferentes. Os URLs oficiais são mutáveis: um download futuro pode não reproduzir o snapshot e deve falhar, não atualizar os oráculos silenciosamente. Preservar privadamente os ZIPs congelados para o ensaio; não contar com recuperação permanente dos mesmos bytes na CVM. O script não é um downloader resiliente de produção.

`profile.py` mede o universo completo. A consulta `joins` demonstra intencionalmente fanout; não a reutilizar para fatos. `cohort.py` seleciona população de modo determinístico, gera calendário e oráculos e faz assertions entre DuckDB e Python Decimal lido dos CSVs originais. Ambas as passagens usam a lista congelada; não constitui revisão adversarial independente.

Fonte/atribuição: Comissão de Valores Mobiliários — [Informe Diário](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario) e [Cadastro](https://dados.cvm.gov.br/dataset/fi-cad), ODbL conforme catálogos. Evidências derivadas mantêm URLs e hashes. Distribuição futura de snapshot/banco deve cumprir a licença; este diretório não publica automaticamente dados ou arquivos na internet.

Contratos e limitações: [relatório](../../specs/cvm-profiling.md), [dados](../../specs/data-contracts.md), [métricas](../../specs/metrics.md).
