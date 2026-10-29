# dbt demo — revisão e proposta

[Revisão de organização e boas práticas dbt](repository-review.md): diagnóstico do repositório, baseline de lint/format, organização aplicada e aceite local antes do agente; [resultados e revisão](../reviews/repository-refactor-review.md).

Data da pesquisa: **28 de outubro de 2026**. Estado: **vertical real de PL/fluxo, ingestão imutável e snapshots implementados; gate semântico UAT e runner Linux ARM64 offline aprovados; workflow GitHub ativado, com resultados no histórico remoto. Projeto completo ainda em evolução**.

1. [Revisão do prompt e pesquisa](research-review.md): evidências, problemas, custos, versões e comparação de datasets.
2. [Design proposto](design-proposal.md): requisitos, arquitetura, grãos, métricas, ambientes e decisões.
3. [Plano por entregas](delivery-plan.md): sequência, critérios de aceitação, revisão adversarial e roteiro da demo.
4. [Avaliação de AI BI](ai-bi-evals.md): casos, oráculos, invariantes e critérios de aprovação.
5. [Prompt revisado](revised-agent-prompt.md): instruções portáveis para o futuro agente implementador, incluindo Wizard opcional.

Stack aprovada pelo usuário: **dbt v2 + DuckDB + MetricFlow local**, apoiada na [prova de compatibilidade executável](compatibility.md). O requisito é não depender de serviços pagos; licença Apache 2.0 integral não é obrigatória. O domínio CVM, o recorte e os contratos foram definidos no profiling abaixo. [Validação complementar de VS Code, linhagem e JSON](compatibility-extended.md).

Design, plano e prompt do implementador foram reconciliados com a stack aprovada. Apenas a pesquisa original preserva o histórico da recomendação Core 1.12. A prova inicial usou dados sintéticos; as entregas posteriores abaixo usam a CVM real.

[Gates finais concluídos no laptop](compatibility-final-gates.md): unit tests nativos, contratos, semiaditividade e pin verificável do driver da documentação. Esses gates antecederam o profiling e as entregas de negócio descritas abaixo.

## Dados reais e contratos — 28/10/2026

- [Profiling CVM e recorte escolhido](cvm-profiling.md): 60 classes, abril–setembro/2026; 7.554 linhas e oráculos reconciliados.
- [Contratos de dados](data-contracts.md): identidade hierárquica, tipos, resolução, proveniência e calendário.
- [Contratos de métricas](metrics.md): PL, fluxo, cotistas e cobertura; retorno/CDA ainda não homologados.

Esta decisão substitui o recorte aproximado anterior. A pipeline de negócio completa continua não implementada.

- [Fixtures e testes de negócio](business-fixtures.md): laboratório sintético com TDD, mutações e revisão adversarial; não equivale à pipeline implementada.

## Primeira vertical implementada

[Resultado, evidências e limites](first-vertical.md): testes nativos dbt, satélite incremental de capturas, fato denso e PL/fluxo/cobertura no MetricFlow local. Este estado substitui menções anteriores de que nenhum modelo de negócio existia. [Comandos](../transform/README.md).

## Atualização: ingestão por sources

A [ingestão CVM](ingestion.md) substitui os seeds descritos anteriormente: ZIPs preservados por SHA-256, envelopes JSON, sources físicos, quarentena e reconciliação por arquivo. População/calendário permanecem contratos congelados. Oráculos e histórico mínimo foram preservados; consulte o documento para escopo e evidências atuais.

## Atualização: publicação de snapshots — 28/10/2026

A [publicação atômica local](snapshot-publication.md) implementa bundles verificados, ponteiros independentes dev/UAT, rollback e leitores read-only fixados na release. Substitui referências anteriores a promoção local pendente. O aceite CI Linux posterior consta na seção CI/UAT abaixo; a pipeline completa permanece fora deste escopo. PL e fluxo permanecem reconciliados com os mesmos seis oráculos reais.

## CI Linux e gate semântico UAT

[Contrato, comandos e operação](ci-uat.md): comparação por total, mês e classe/dia, igualdade de inputs, bloqueio de regressões e workflow com bootstrap online/aceite offline. [Revisão independente](../reviews/ci-uat-review.md).

## Publicação como portfólio

[GitHub Actions remoto, desenvolvimento sem Docker e baseline durável](portfolio.md). Repositório público e baseline imutável publicados; CI remoto ativado. Consultar o runbook para os resultados e a correção identificada no primeiro run.
