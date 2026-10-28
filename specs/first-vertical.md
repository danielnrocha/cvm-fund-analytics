# Primeira vertical mínima — 28/10/2026

Implementação em [transform/](../transform/README.md), com dbt v2 2.0.9, DuckDB e MetricFlow local nos ambientes previamente fixados. Escopo: 60 classes, 7.554 observações reais, 7.560 pares esperados no calendário. Sem dependência de serviço pago.

## Modelos e decisões

| Modelo | Responsabilidade |
|---|---|
| `stg_observations` | Interface tipada do snapshot; nesta fatia lê seed delimitado, não extractor genérico |
| `int_resolved` | Normaliza máscara válida; aceita só classes sem subclasses do perímetro; rejeita unknown/ambiguous; agrupa cadastro antes de join para evitar fanout |
| `int_daily` | Uma linha por captura/entidade/dia; preserva conjunto de source IDs; conflito compara todos os seis campos financeiros disponíveis |
| `sat_daily_report` | Append incremental, versão identificada por SHA-256 de array JSON captura/entidade/data; replay idempotente, sem apagar versões |
| `current_daily` | Última captura por timestamp observado; não usa ordem lexical do identificador nem data de competência como watermark |
| `fct_daily` | População × calendário, left join do corrente; PL e fluxo NULL em ausência; reported=0, expected=1 |
| `time_spine` | Dias civis do semestre para consultas MetricFlow |

Contrato nativo de colunas aplicado ao fato. PL DECIMAL(17,2); subtração com operands previamente ampliados e fluxo DECIMAL(38,2). Classificação é `at_capture`, não histórico cadastral. O snapshot importado usa os hashes/proveniências já congelados; não simula histórico real que não foi capturado.

Esta entrega implementa um **satélite mínimo de observações**, não o Data Vault completo do roadmap. Hubs persistentes, links, prestadores, dimensão SCD2, source JSON/quarentena e release bundle continuam pendentes. O seed tipado é uma escolha delimitada para validar a vertical antes de generalizar ingestão.

## TDD nativo e integração

- `01-native-red.log`: quatro falhas de comparação em cinco testes contra modelos incompletos; o caso A→B→A já passava no esqueleto e não é anunciado como vermelho.
- `03-dense-red.log`: fixture do calendário esperado falha com seis linhas ausentes; implementação densa fica verde.
- `06-history-red.log`: seleção da primeira captura falha; corrigida para timestamp mais recente.
- `07-real-oracle-red.log`: população incompleta falha contra 7.560 pares; importação congelada produz seis oráculos exatos.
- `12-history-integration-red.log`: segunda captura apagava a primeira; append idempotente corrigiu.
- `16-gates-red.log`: quatro entradas inválidas passavam; bloqueios de required fields, capture FK e imutabilidade foram adicionados antes do aceite.

Logs em [evidence](../transform/evidence/). A suíte nativa inclui identidade/nível, fanout, duplicatas, conflito, A→B→A, latest timestamp, missing/zero, precisão de fluxo e população vazia. Integração em diretório temporário comprova deltas A→B→A, replay e equivalência com rebuild que recebe **todas** as capturas.

Gates de dados bloqueiam nulos obrigatórios, identidade não resolvida, captura inexistente, dimensão duplicada, conflito de payload e alteração de versão imutável no incremental. `dbt build` aplica os gates; `dbt run` não é comando de aceite. Full-refresh reconstrói a fonte fornecida e não é instrumento para manter deltas antigos ausentes dos inputs.

## Resultado no MetricFlow local

Seis meses reconciliados exatamente com [oráculos reais](../profiling/cvm/evidence/monthly-oracles.json). Total abril–setembro:

- PL no último corte: **R$ 119.385.193.058,06**; não soma de estoques mensais.
- Fluxo reportado: **R$ 4.725.910.556,15**, parcial: 7.554/7.560 pares.
- Fechamentos mensais: 60/60 classes; lacunas intramês continuam visíveis na cobertura de fluxo.
- Classe associada ao CNPJ 31963249000126 em 28/08: PL/fluxo NULL, cobertura 0/1, inclusive com filtro por entidade. Não recua ao dia anterior.
- Mutações semânticas: remover non-additivity produz PL incorreto e é detectado pelo oráculo, em projeto descartável.

As métricas publicadas nesta vertical são `reported_net_assets_eop`, `net_flow`, contagens de reporte/esperado e razões de cobertura. Último disponível por entidade, cotistas, retornos e carteira continuam fora da publicação. Não há agente/API que impeça um usuário de consultar fluxo sem cobertura: a apresentação deve mostrar os dois. Gate futuro do gateway continua necessário.

## Revisão e limites

[Parecer independente](../reviews/first-vertical-review.md) registra achados, correções e revalidação. O revisor não recebeu o histórico de raciocínio do autor e usou banco temporário.

Build não é promoção atômica: falhas podem deixar intermediários alterados. Não servir o arquivo de trabalho como produção. Histórico original depende de preservar capturas; reconstruir com delta apenas perde passado. Precisão extrema foi testada no SQL nativo; não se promete transporte decimal arbitrário pelo CLI do MetricFlow além dos valores reais reconciliados. CI Linux, UAT/release, rollback e integração completa de ingestão permanecem pendentes.

## Verificação final

Build final com análise estrita e rede bloqueada: **40 recursos bem-sucedidos — 7 modelos, 4 seeds, 20 testes de dados e 9 unit tests nativos**. O dbt v2 emite aviso de ausência de `dbt_cloud.yml` para sua validação semântica embutida; `mf validate-configs` foi executado separadamente e passou sem erros/warnings. Consultas semânticas e oráculos também passaram com rede bloqueada. Evidências finais: `19-final-build.log`, `20-offline-semantic.log`, `21-final-oracles.log` e `22-final-rejection-gates.log`.

Tasks de build e verificação semântica adicionadas em `.vscode/tasks.json`; os comandos foram executados no terminal, sem repetir um ensaio interativo da UI do VS Code nesta entrega.

## Atualização: ingestão por sources

A [ingestão CVM](ingestion.md) substitui os seeds descritos anteriormente: ZIPs preservados por SHA-256, envelopes JSON, sources físicos, quarentena e reconciliação por arquivo. População/calendário permanecem contratos congelados. Oráculos e histórico mínimo foram preservados; consulte o documento para escopo e evidências atuais.

## Atualização: publicação de snapshots — 28/10/2026

A [publicação atômica local](snapshot-publication.md) implementa bundles verificados, ponteiros independentes dev/UAT, rollback e leitores read-only fixados na release. Substitui referências anteriores a promoção local pendente; CI Linux e pipeline completa continuam fora deste aceite. PL e fluxo permanecem reconciliados com os mesmos seis oráculos reais.
