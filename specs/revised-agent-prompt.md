# Prompt revisado para o agente implementador

> Stack aprovada pelo usuário em 28/10/2026: **dbt v2 + DuckDB + MetricFlow local**, sem serviços pagos obrigatórios. A implementação completa ainda não foi iniciada. Evidências e limites: [compatibilidade](compatibility.md) e [editor, linhagem e JSON](compatibility-extended.md).

Use este prompt depois de aprovar o design. Ele é intencionalmente independente de Wizard, Claude ou Codex. As specs são canônicas; este texto não as duplica.

---

Você está ajudando Daniel a preparar uma demo avançada de dbt com dados públicos, foco em métricas confiáveis para AI BI. Leia `specs/README.md`, `research-review.md`, `design-proposal.md`, `delivery-plan.md` e `ai-bi-evals.md` antes de agir.

Primeiro confirme quais decisões foram aprovadas. Se ainda estiver em revisão de arquitetura, apenas revise documentos; não implemente a pipeline. Depois de autorizado, trabalhe por entregas do plano, com evidência de aceitação antes de avançar.

Restrições:

1. Stack aprovada: dbt v2 2.0.9 + DuckDB + MetricFlow local, Python 3.12/uv e VS Code. Não substituir por Cloud ou serviço pago. Siga as versões e os dois ambientes de `specs/compatibility.md`; upgrades exigem repetir probes, não usar latest.
2. Manter `.venv-dbt` para transformação v2 e `.venv-mf` para `dbt-metricflow[dbt-duckdb]` 0.15.0. Core Python é dependência interna do mf, não deve produzir modelos/manifestos. Reutilizar os probes comprovados de unit test nativo, contrato e semiaditividade em `compatibility-final-gates.md`. Driver de docs é fixado por hash para Darwin-arm64; usar `pinned_docs.py` e criar lock próprio antes de CI Linux.
3. CVM foi encontrada no catálogo da Base dos Dados, mas Informe Diário tratado estava pago. Use recursos originais oficiais da CVM para a baseline gratuita. Se a decisão aprovada for usar BD gratuita diretamente, siga o dataset BTS e escreva os contratos correspondentes antes de implementar.
4. Descubra recursos e colunas; não adivinhe tabelas ou arquivos. Preserve originais, checksums, licença e data da captura. CI e palco usam snapshots locais reproduzíveis.
5. Não presuma fundo × dia. Valide fundo/classe/subclasse, identidade, unicidade e aditividade econômica de cada campo. Não some totais repetidos entre níveis hierárquicos.
6. Arquivos JSON entram por landing física com payload original, checksum e linha; parsing e quarentena ficam em SQL. Não desabilitar análise estrita globalmente para aceitar read_json direto. JSON produzido de CSV deve ser identificado como envelope derivado. Não invente hierarquias nem revisões reais; fixtures sintéticas permanecem rotuladas.
7. Bronze preserva versões e erros com proveniência. Raw Vault é append-only e idempotente; resolva versão vigente no Business Vault. Não use delete+insert ou microbatch destrutivo como fallback do Raw Vault.
8. Implemente apenas os padrões DV necessários. Prefira SQL explícito revisável a uma biblioteca genérica. Hashing deve distinguir null, vazio, delimitadores, tipos e leading zeros; preservar transições A→B→A.
9. Defina grãos antes de escrever joins. Não una fatos diários e posições mensais linha a linha. Resolva SCD2 por chave e vigência; não projete cadastro atual no passado sem evidência.
10. Usar nova sintaxe semântica embutida nos modelos; executar `mf validate-configs` localmente. Não depender de `dbt sl`. Semantic YAML segue exatamente a versão escolhida. Métricas devem declarar população, tempo, unidade, missing, cobertura e rollups permitidos. Contas reportadas não são investidores únicos; PL é semiaditivo; retorno acumulado não é média; posição confidencial não é zero.
11. TDD para lógica: teste com resultado conhecido → falha observada → implementação mínima → verde → refatoração. Unit tests não substituem testes de estado final de incrementais. Prove replay, correção tardia, rebuild equivalente e rollback.
12. CI obrigatório constrói fixture inteira. Slim CI exige baseline físico correspondente ao manifest e acesso read-only. Não trate `dbt clone` DuckDB como zero-copy físico. Mudanças só em métricas disparam regressão semântica.
13. UAT compara candidato e baseline com inputs iguais. Promova o mesmo SHA/locks/snapshot aprovado. Identifique limitações de GitHub Free e repo privado; não prometa required reviewers que o plano não oferece.
14. Exponha ao agente somente ferramentas de métricas validadas e leitura. Retorne SQL, versão, snapshot, cobertura e proveniência. Não permita SQL livre ou shell como escape automático. O MCP oficial não garante endpoint semântico local sem configuração/implementação adicional.
15. Rode evals determinísticos sem LLM por padrão. Testes de agente real só contam quando executados com modelo real; replay e mocks devem ser declarados. Reporte falhas por categoria, não só média global.
16. Wizard é opcional e sujeito a trial/créditos/provedor. Não o instale nem configure conta durante a revisão de arquitetura. O projeto deve continuar funcionando sem ele. Configure MCP no cliente real; não execute `claude mcp add` se o host for outro.
17. Ao terminar cada entrega implementada, solicite revisão independente a outro agente ou humano com spec/diff/testes. Corrija findings bloqueantes; não assine a própria revisão. Evidência documental pode validar custo/licença; não invente teste executável para isso.
18. Gerar linhagem por `dbt compile --static-analysis strict --generate-info-schema` e `pinned_docs.py` para exportar docs com o driver fixado; conferir arestas. VS Code tasks usam caminhos explícitos; não depender de login/LSP não homologado. Atualize specs/ADRs e comandos do README com o comportamento realmente verificado. Poucos commits coerentes, sem publicar PR/comentário/mensagem sem autorização aplicável. Não anuncie production-grade como SLA operacional que não foi construído.

Comece pela Entrega 0. Produza a matriz de compatibilidade e liste qualquer premissa que falhou. Não construa oito camadas em paralelo antes de provar um caminho completo de dados até uma métrica correta.

## Atualização normativa de dados reais

Leia também `specs/cvm-profiling.md`, `specs/data-contracts.md` e `specs/metrics.md`. O recorte fixo é 60 classes, abril–setembro/2026, 7.554 observações. Não resselecione universo a cada carga. Não trate cadastro bruto como dimensão única; há duplicatas e fanout comprovados. Cadastro atual não prova atributos históricos. Retornos e CDA não estão publicados. Próxima entrega é fixtures/TDD de negócio, não implementação automática da pipeline inteira.

## Estado após implementação autorizada da primeira vertical

Leia `specs/first-vertical.md` e `transform/README.md`. A primeira vertical PL/fluxo/cobertura existe, com testes dbt nativos, histórico incremental mínimo e consultas MetricFlow verificadas. Isso substitui a instrução anterior de que fixtures eram o próximo passo. Demais entregas só devem avançar conforme escopo autorizado; não declarar a pipeline inteira concluída.

## Atualização: ingestão por sources

A [ingestão CVM](ingestion.md) substitui os seeds descritos anteriormente: ZIPs preservados por SHA-256, envelopes JSON, sources físicos, quarentena e reconciliação por arquivo. População/calendário permanecem contratos congelados. Oráculos e histórico mínimo foram preservados; consulte o documento para escopo e evidências atuais.
