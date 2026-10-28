# Compatibilidade executável — 28/10/2026

**Veredito: stack aprovada pelo usuário e núcleo validado com ressalvas operacionais.** dbt v2 + DuckDB + MetricFlow local é a baseline definitiva. Não constitui aprovação da arquitetura inteira nem implementação da demo.

O requisito vigente é não depender de serviços pagos; licença integralmente Apache 2.0 não é obrigatória. Esta evidência substitui a recomendação conservadora anterior de Core 1.12 como motor principal. Core permanece dependência interna do pacote MetricFlow.

## Ambiente e versões

macOS 15.5, Darwin arm64, Python 3.12.13. dbt 2.0.9 em um ambiente; dbt-metricflow 0.15.0, MetricFlow 0.213.0, dbt-duckdb 1.11.1, dbt-core 1.12.6 e DuckDB Python 2.0.0 em outro. O motor v2 reportou DuckDB embutido v1.5.4. Dois runtimes DuckDB acessaram sequencialmente o mesmo arquivo; concorrência não foi testada.

## Evidência

[Fixture, runner e instruções](../compatibility/dbt-v2-metricflow/README.md), [25 resultados aprovados](../compatibility/dbt-v2-metricflow/evidence/results.json) e [resumo da execução](../compatibility/dbt-v2-metricflow/evidence/run-summary.log).

| Capacidade | Resultado observado |
|---|---|
| Build v2 + DuckDB | Quatro modelos, um seed e três data tests aprovados |
| Nova sintaxe semântica | Manifesto gerado pelo v2 e consumido pelo MetricFlow |
| Validação local MetricFlow | Sem erros semânticos ou de banco |
| Consultas | Total, dia, mês, região e filtro conferidos contra oráculos explícitos |
| Métrica derivada | Receita 1.000, custo 600, margem 40%; média por remessa seria incorreta (37,5%) |
| Rejeição | Métrica e dimensão inexistentes rejeitadas com código não zero |
| Incremental | Reexecução sem duplicatas e correção de receita 1.000 → 1.050, mantendo quatro registros |
| JSON | Objeto aninhado, cast decimal e campo ausente tratados |
| Independência de serviço | Processos executados sob sandbox com rede bloqueada; controle confirmou negação de socket |
| Documentação | Gerada offline após baixar dependência de driver no bootstrap |
| Linhagem de modelos | Manifesto v2 registra fct_shipments → seed shipments |

## Ressalvas para a spec

1. Usar caminhos explícitos para os executáveis; não misturar instalações que exportam o comando `dbt`. O mf chama Core `debug` internamente para configurar o adapter, mas não fizemos build/parse Core. O hash do manifesto permaneceu inalterado durante as consultas.
2. Usar nova sintaxe semântica. A tentativa com YAML legado gerou aviso e não produziu o manifesto necessário; não houve edição manual do manifesto nem patch de bibliotecas.
3. Incluir `mf validate-configs` como gate local obrigatório. O build v2 emite aviso de que pula a validação conectada sem dbt_cloud.yml; isso não bloqueou as consultas locais.
4. Preparar dependências antes da apresentação. `dbt docs generate` inicialmente falhou offline tentando obter driver; após uma execução online, repetiu com sucesso sem rede. O driver de bootstrap ainda precisa de distribuição explicitamente fixada na futura infraestrutura; os locks atuais fixam os pacotes Python.
5. Atualização: análise estrita, arestas de linhagem de colunas e execução no VS Code foram investigadas na [validação complementar](compatibility-extended.md), que substitui esta pendência inicial.
6. Atualização: JSON externo via landing física e análise estrita passaram na [validação complementar](compatibility-extended.md). Leitura direta com read_json apresentou limitação na análise estrita. httpfs/spatial continuam fora da evidência.
7. Não foram testados fonte real, Data Vault, joins multifato, saldos semiaditivos, contratos, unit tests dbt, snapshots, escala, CI Linux ou agente de IA. As próximas entregas devem validar esses comportamentos sem reinterpretar esta prova como cobertura completa.

## Fontes primárias usadas

- [Instalação v2](https://docs.getdbt.com/docs/local/install-dbt)
- [DuckDB e limitações](https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup)
- [MetricFlow local versus plataforma](https://docs.getdbt.com/docs/build/metricflow-commands)
- [Nova especificação semântica](https://docs.getdbt.com/docs/build/latest-metrics-spec)

As conclusões de execução acima são sustentadas pelos logs locais, não apenas por documentação.

## Atualização dos gates finais

As pendências locais de unit tests, contrato de tabela, semiaditividade e driver de docs foram resolvidas e verificadas em [compatibility-final-gates.md](compatibility-final-gates.md). Esse relatório substitui os limites históricos acima para essas capacidades; fonte real e CI multiplataforma continuam fora da prova.
