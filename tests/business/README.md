# Laboratório de contratos de negócio

Escopo: especificação executável isolada, com fixture sintética reduzida e agregação real em DuckDB. Não é parser dos CSVs CVM, modelo dbt, implementação do Vault ou validação do MetricFlow. Nenhum download é necessário.

```sh
compatibility/dbt-v2-metricflow/.venv-mf/bin/python -m unittest discover -s tests/business -v
compatibility/dbt-v2-metricflow/.venv-mf/bin/python tests/business/mutation_check.py
```

`fixtures/observations.json` tem duas entidades fictícias, duas datas e uma repetição física. Os CNPJs são identificadores de teste de 14 dígitos, não cadastros reais; checksum cadastral não faz parte do probe. `kind=CLASS/FUND` é namespace interno explícito, não mapeamento já implementado de TP_FUNDO_CLASSE. `source=file1:2` é uma proveniência simplificada, não o manifest completo de produção. `pl` e `flow` são campos previamente tipados/conceituais: o parsing lexical, escala e todos os demais campos CVM serão testados na entrega de ingestão.

Oráculos manuais: três observações lógicas, quatro físicas; PL 100+200+110 = 410 apenas para verificar conservação em joins (não métrica temporal publicável). No corte 02/04, PL=110, uma de duas entidades presente; fluxo reportado=30, três de quatro pares presentes. A observação A/02 tem fluxo zero real, diferente da observação B/02 ausente. No corte 03/04 não existe PL; não recuar para 02/04. Todos os valores são sintéticos.

Casos adicionais são construídos explicitamente nos testes: conflito só no fluxo; histórico de capturas A→B→A; mesmo identificador em namespaces diferentes; ID de subclasse repetido sob dois pais; CNPJ malformado; cadastro ausente ou ambíguo; dimensão que multiplicaria fato; população vazia e fato duplicado.

TDD: `evidence/01-red.log` registra 12 testes contra stubs retornando vazio, com 14 falhas de assertions (subtests incluídos), sem erros de importação. `02-green.log` registra primeira implementação mínima verde. Mutações rodam em diretórios temporários, sem alterar o probe original; os logs explicam o defeito detectado. Histórico sintético A→B→A testa separação de capturas, não persistência, ordenação temporal, merge incremental ou replay de uma pipeline real.

O caminho de migração é portar esses inputs e oráculos para unit tests nativos dbt e testes de integração dos modelos efetivos. Não duplicar a lógica Python como motor de produção nem anunciar estes testes como prova de um modelo dbt ainda inexistente.

Revisão adversarial: teste de limite adicional documentado em `evidence/03-review-red.log`; correção para fluxo DECIMAL(38,2), seguida de 13 testes verdes em `04-final-green.log`. Veja [parecer independente](../../reviews/business-fixtures-review.md).
