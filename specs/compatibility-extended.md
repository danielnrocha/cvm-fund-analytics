# Validação complementar — editor, linhagem e JSON

Data: 28/10/2026. **Stack aprovada: dbt v2 2.0.9 + DuckDB + MetricFlow local.** Escopo autorizado: especificação e probes; projeto completo não implementado.

## Decisão e matriz de resultado

| Item | Evidência executável | Decisão |
|---|---|---|
| VS Code básico | VS Code 1.143.1 arm64, extensão dbtLabsInc.dbt 0.122.0 ativada, arquivo SQL aberto, build executado por tarefa do extension host com exit 0 | Aprovado para editar/executar a demo |
| LSP | Servidor 2.0.9 iniciou e registrou compilação incremental com DuckDB; teste de coluna inexistente não gerou diagnóstico na janela de 12 segundos | Não prometer detecção SQL avançada; usar compile/build estrito como gate |
| Painel visual de linhagem da extensão | Comando registrado, mas visualização não foi homologada | Opcional; não é dependência da demo |
| Linhagem de colunas no CLI/docs | Arestas concretas em `dbt.column_lineage.parquet`, incluindo seed → fato e source.payload → staging.revenue | Aprovado, com análise estrita e teste das arestas |
| JSON externo direto | `read_json` com schema explícito executa; análise estrita falha em `format` (dbt0227) | Não usar esse caminho nos modelos principais |
| JSON externo por landing | Transporte preserva linhas, checksum e payload; parsing SQL passa build estrito, inclusive casos inválidos | Caminho aprovado |

A ausência de diagnóstico não prova que todo o LSP é incompatível: o teste é limitado a esta versão, configuração local sem login e janela observada. A documentação oficial ainda classifica DuckDB como CLI only. Não confundir ativação da extensão com homologação de todas as funcionalidades.

## Evidências e reprodução

- [Resultado do VS Code](../compatibility/dbt-v2-metricflow/evidence/25-vscode.json).
- [Log LSP](../compatibility/dbt-v2-metricflow/evidence/vscode-lsp.log) e [trace](../compatibility/dbt-v2-metricflow/evidence/vscode-lsp-trace.log).
- [Teste do extension host](../compatibility/vscode-probe-extension/test.js): ativa a extensão real, abre SQL, testa diagnóstico e executa uma tarefa de build. Não usa mocks do VS Code.
- [Runner JSON/linhagem](../compatibility/dbt-v2-metricflow/verify_extended.py) e [resultados](../compatibility/dbt-v2-metricflow/evidence/extended-results.json).
- [Falha esperada do JSON direto](../compatibility/dbt-v2-metricflow/evidence/20-external-json.log) e [sucesso de runtime](../compatibility/dbt-v2-metricflow/evidence/21-external-json-runtime.log).
- [Build estrito](../compatibility/dbt-v2-metricflow/evidence/27-build-strict.log) e [docs com linhagem](../compatibility/dbt-v2-metricflow/evidence/28-docs-column-lineage.log).
- [Tarefas VS Code](../compatibility/dbt-v2-metricflow/.vscode/tasks.json).

Repetir os comandos do README da prova. `run_probe.py` verifica novamente o núcleo; `verify_extended.py` verifica a alternativa de JSON e as arestas. A versão anterior tinha 25 verificações; acrescentamos o preparo da landing ao runner principal. O runner estendido verifica 14 propriedades, além do controle negativo de análise e do controle positivo de execução direta.

Para repetir o teste do editor, usar o CLI do VS Code com `--extensionDevelopmentPath` apontando a `compatibility/vscode-probe-extension`, `--extensionTestsPath` para seu `test.js`, `--extensions-dir` para a pasta isolada que contém dbtLabsInc.dbt 0.122.0, e `--user-data-dir` para um perfil de teste novo. Abrir `compatibility/dbt-v2-metricflow` como raiz. Definir `dbt.dbtPath` para o binário `.venv-dbt/bin/dbt` e `DBT_PROFILES_DIR` para a raiz da prova. Reutilizar um processo VS Code aberto pode fazer o CLI encaminhar a abertura à janela existente sem executar novamente o harness: exigir timestamp e conteúdo novo de `25-vscode.json`, não apenas exit 0 do launcher.

A instalação da extensão foi feita somente em `compatibility/vscode-sandbox/extensions`; não alterou o conjunto de extensões do perfil habitual. Os perfis descartáveis ficam ignorados pelo Git. O teste do editor usou rede normal e nenhum login dbt foi configurado; a prova offline aplica-se aos processos CLI/dados, não ao editor inteiro.

## Caminho de JSON aprovado

1. Ler arquivo JSONL em transporte e preservar cada linha como VARCHAR com SHA-256 e número da linha. Nenhuma regra financeira em Python.
2. Declarar a tabela física como `source()` com tipos explícitos.
3. No staging, usar `try_cast(payload as json)` e extração/casts explícitos. Atribuir `malformed_json` ou `invalid_revenue` sem apagar o payload.
4. Reconciliar aceitos/rejeitados; campos novos permanecem recuperáveis no raw.
5. Aplicar política de promoção da spec: preservar uma linha inválida não significa publicá-la em marts.

Fixture: objeto aninhado, decimal 125,50, null, array vazio, array ausente, campo novo, número inválido e JSON malformado. A prova preservou quatro linhas e classificou dois motivos de rejeição. Não houve inferência de regras do dataset real.

Linhagem comprovada: `source.raw_json_fixture.payload → stg_external_json.revenue`. O compilador acompanha colunas; não afirmamos que conhece automaticamente o JSONPath `$.shipment.revenue` nem a proveniência de cada linha. Esses detalhes pertencem ao contrato de parsing e aos metadados de captura.

## Geração correta de linhagem

```sh
.venv-dbt/bin/dbt compile --profiles-dir . --static-analysis strict --generate-info-schema
.venv-dbt/bin/dbt docs generate --profiles-dir . --no-compile
```

No 2.0.9, passar `--static-analysis strict` diretamente para `docs generate` falhou como argumento desconhecido, apesar da sugestão do próprio comando. Compilar separadamente e exportar o índice existente funcionou. Não rodar docs com recompilação padrão depois e presumir que manteve a análise estrita.

O arquivo de linhagem final teve 14 arestas na fixture estendida; o teste confere as duas arestas críticas nominalmente. Não reivindicamos validação visual do grafo no navegador ou no painel da extensão com base apenas nesse arquivo.

## Limites restantes

Unit tests nativos em vermelho/verde, contrato de tabela, métricas semiaditivas e pin do driver Darwin foram resolvidos nos [gates finais](compatibility-final-gates.md). Joins multifato, fonte real, escala e CI Linux continuam no plano. Nenhuma limitação encontrada exige serviço pago ou mudança da stack aprovada.

Fontes primárias consultadas: [instalação da extensão](https://docs.getdbt.com/docs/install-dbt-extension), [suporte de adapters](https://docs.getdbt.com/docs/supported-data-platforms) e [limitações DuckDB](https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup). Os resultados da tabela são observações locais, não garantias gerais do fornecedor.
