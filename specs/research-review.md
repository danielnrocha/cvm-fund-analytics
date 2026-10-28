# Revisão técnica do prompt e pesquisa

Verificado em 2026-10-28. Este documento distingue fatos publicados, observações de catálogo e recomendações de design. Não é uma certificação de compatibilidade em runtime.

## Parecer

O domínio escolhido pelo Claude é excelente para ensinar semântica, temporalidade e qualidade. O prompt, porém, **não deve ser executado como está**. Seus principais problemas são de grão e preservação histórica, além de premissas de acesso gratuito e CI.

Eu discordo de tratar “arquitetura de mercado” como uma lista obrigatória de tecnologias. Data Vault não é pré-requisito para BI confiável nem para dbt avançado. Neste projeto ele se justifica como conteúdo didático e como mecanismo de auditoria de revisões; não justifica construir uma biblioteca completa de Data Vault.

## O que mudou no ecossistema

O blog oficial de setembro/2026 diferencia **dbt v2**, sucessor do Fusion, de **dbt OSS**, a distribuição Apache 2.0. A geração Python continua na série 1.x. Gratuito, local e inteiramente open source são propriedades diferentes. Não substituir silenciosamente o Core pedido pelo usuário pelo binário v2 completo. [Comparação oficial](https://docs.getdbt.com/blog/comparing-dbt-and-dbt-oss), [versões](https://docs.getdbt.com/docs/dbt-versions).

| Caminho | Benefício | Limitação | Decisão proposta |
|---|---|---|---|
| Core Python 1.12.x + dbt-duckdb | Respeita literalmente o pedido e o ecossistema Python do prompt | Não é a geração mais recente | Baseline recomendado |
| dbt OSS 2.x + DuckDB | Runtime Apache moderno | Paridade do adapter e ferramentas precisam de validação | Comparação opcional, não segunda stack obrigatória |
| dbt v2 completo + extensão oficial | Recursos locais de desenvolvimento mais ricos | Não é todo Apache; altera o requisito literal | Somente com escolha explícita do usuário |

A documentação classifica DuckDB v2 como GA **CLI only**, aponta limitações de análise de arquivos locais e um caminho específico para carregar extensões. Portanto, a existência de suporte ao banco não prova paridade de todos os recursos da extensão VS Code. [Plataformas](https://docs.getdbt.com/docs/supported-data-platforms), [DuckDB v2](https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup).

### Versões e sintaxe

Consulta direta aos metadados públicos PyPI encontrou Core **1.12.6**, dbt-duckdb **1.11.1**, dbt-metricflow **0.15.0**, dbt-oss **2.0.8** e DuckDB **2.0.0**. São versões publicadas observadas, **não um conjunto já testado**. Não instalar automaticamente todos os “latest”. O bundle MetricFlow 0.15.0 declara Core >=1.11,<1.13 e MetricFlow ==0.213.0. Seu extra é **`dbt-duckdb`**, portanto o candidato correto é `dbt-metricflow[dbt-duckdb]`, não `[duckdb]`. [Core](https://pypi.org/pypi/dbt-core/json), [bundle](https://pypi.org/pypi/dbt-metricflow/json), [adapter](https://pypi.org/pypi/dbt-duckdb/json), [DuckDB](https://pypi.org/pypi/duckdb/json), [OSS](https://pypi.org/pypi/dbt-oss/json).

O prompt acertou pontos que não devem ser “corrigidos” com conhecimento antigo: Core 1.12 documenta YAML semântico embutido nos modelos, leitura de `.env` no diretório corrente e `latest_version_pointer`. Atenção: com projeto em `transform/`, o diretório de execução importa para `.env`. A configuração do pointer é `latest_version_pointer.enabled`, não uma propriedade vaga. [Upgrade 1.12](https://docs.getdbt.com/docs/dbt-versions/dbt-upgrade/upgrading-to-v1.12).

A nova sintaxe usa `semantic_model` sob o modelo, entidades/dimensões nas colunas e `metrics` como irmão de `semantic_model`. `non_additive_dimension` usa `name`, `window_agg`, `group_by`; não misturar com `window_choice/window_groupings` da sintaxe antiga. A regra de negócio precisa ser validada além do parse. [Migração YAML](https://docs.getdbt.com/docs/build/latest-metrics-spec), [referência](https://docs.getdbt.com/reference/semantic-layer-reference).

## Gratuidade real

| Componente | O que podemos afirmar | Consequência |
|---|---|---|
| Core, DuckDB, MetricFlow local | Software disponível sem licença comercial obrigatória; MetricFlow >=0.209 é Apache | Base reproduzível local |
| dbt Wizard | CLI beta; trial de 30 dias e US$100 em créditos em conta elegível; BYOK e assinatura pessoal OpenAI são opções documentadas | Opcional; não prometer IA gratuita para sempre |
| Semantic Layer hospedada | Produto da plataforma, separado da biblioteca MetricFlow | Não usar endpoint hospedado na baseline |
| Power User | Linhagem de modelos sem API key; coluna exige key e tem regras de créditos | Garantir DAG gratuito; coluna é extra sujeito a quota |
| BigQuery | Free tier limitado, separado do direito de acessar dados pagos da BD | Não torna CVM tratado grátis; usar arquivos CVM |
| GitHub | Proteções de environments dependem do plano e visibilidade do repo | Não prometer aprovação obrigatória gratuita em repo privado |
| Inferência de LLM | Modelo local pode evitar cobrança por API, mas usa hardware; assinatura existente também não é software gratuito | Separar custo do pipeline e do assistente |

Fontes: [Wizard](https://docs.getdbt.com/docs/platform/wizard-overview), [MetricFlow e licença](https://github.com/dbt-labs/metricflow), [Semantic Layer hospedada](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl), [linhagem Power User](https://help.altimate.ai/dbt-power-user/test/lineage/), [créditos Power User](https://help.altimate.ai/dbt-power-user/arch/pricingfaq/), [BigQuery](https://cloud.google.com/bigquery/pricing), [GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

O core da demo deve funcionar com fixtures e consultas semânticas determinísticas mesmo sem conta Wizard, LLM, GCP ou Altimate. Demonstrar agente real exige escolher uma inferência disponível; replay de respostas é fallback de apresentação e deve ser identificado como replay.

## Investigação de datasets

O site da BD foi consultado pelo navegador integrado. As buscas por siglas ANTAQ/ANAC devolveram resultados amplos e inconsistentes; não são evidência de inexistência de datasets. A comparação abaixo usa páginas de datasets efetivamente observadas.

| Dataset | Evidência observada | Potencial didático | Decisão |
|---|---|---|---|
| CVM — Fundos de Investimento | 6 tabelas tratadas e 7 fontes originais; Informe Diário de 7,71 GB, cobertura 2000-01-03 a 2026-10-26 marcada PAGO | Estoque vs fluxo, revisões, hierarquia fundo/classe, carteira mensal, confidencialidade | Melhor domínio; ingerir da CVM direta |
| BTS — Pontualidade de Voos Domésticos | Tabelas Voos e Aeroportos; Voos de 89,72 GB; faixa grátis 1987-10 a 2026-02 | Cancelamentos, desvios, papel origem/destino, horário local, taxas com denominador correto | Melhor alternativa se BD gratuita direta for obrigatória |
| PRF — Acidentes em Rodovias Federais | Resultado do catálogo: 3 tabelas, 2007-01-01 a 2026-08-31, recursos grátis e pagos | Acidente × pessoa × veículo e fanout; segurança viária, não operação logística de carga | Alternativa secundária; acesso por tabela não validado |

Links: [CVM na BD](https://basedosdados.org/dataset/9c5a820f-09dd-4519-adfd-611819163ae0?table=b93cd010-3ca6-472f-9726-b0578178c72c), [BTS na BD](https://basedosdados.org/dataset/3f7c078a-008e-407f-bbc7-45153d9a9b5e?table=694708a7-b3ad-4305-9a4e-1b4875cccdec), [PRF na BD](https://basedosdados.org/dataset/d8f20719-cd6b-41cb-8386-76ed91565a78).

IDs BigQuery observados: `basedosdados.br_cvm_fi.documentos_informe_diario` e `basedosdados.us_dot_bts_ontime.flight`. Nenhum foi consultado via BigQuery nesta revisão. O catálogo CVM mostra `id_fundo` descrito como tipo, `regate_dia` com essa grafia e valores monetários FLOAT64: exemplos concretos de por que não adivinhar significado ou copiar nomes de memória. O dicionário original deve prevalecer na ingestão direta.

### Por que manter CVM

A fonte oficial oferece cadastro de fundos/classes/subclasses, informes diários e carteiras CDA em arquivos. O dicionário atual do informe inclui `CNPJ_FUNDO_CLASSE`, `ID_SUBCLASSE`, `TP_FUNDO_CLASSE` e `DT_COMPTC`. Valores monetários são descritos como numeric(17,2), e quota como numeric(27,12). **Fundo × dia não está validado como grão.** [Cadastro](https://dados.cvm.gov.br/dataset/fi-cad), [Informe](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario), [dicionário do informe](https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/META/meta_inf_diario_fi.txt).

CDA tem blocos heterogêneos, arquivos de posições confidenciais consolidadas e particularidades de fundos estruturados. Uma carteira não é necessariamente uma lista pública completa de ativos. O catálogo original também documenta reapresentações, inclusive de meses antigos. [CDA](https://dados.cvm.gov.br/dataset/fi-doc-cda), [dicionários CDA](https://dados.cvm.gov.br/dados/FI/DOC/CDA/META/meta_cda_fi_txt.zip).

Recomendação: recorte fixo de seis meses encerrados, escolhido após profiling; coorte de aproximadamente 50–100 entidades reportantes selecionadas deterministicamente, com estratos de tipo/tamanho e casos complexos. Uma amostra de top 500 fundos no fim do período induz viés de tamanho, sobrevivência e seleção com informação futura. A demo deve dizer “coorte demonstrativa”, nunca inferir automaticamente todo o mercado.

### Semiestruturado sem teatro

CSV dentro de ZIP continua tabular. Transformá-lo em JSON não torna a fonte nativamente semiestruturada. Preservar os bytes originais, capturar metadados JSON do catálogo CKAN e, se quisermos ensinar arrays de posições, produzir um **envelope derivado de integração**, documentado e reversível. Não inventar classes, subclasses ou reenvios reais. Fixtures sintéticas para revisões são legítimas quando rotuladas como sintéticas.

## Achados na arquitetura original

| Prioridade | Achado | Correção exigida |
|---|---|---|
| P0 | Grão fundo × dia ignora classes/subclasses | Profiling de chaves e contrato de entidade reportante antes dos marts |
| P0 | Dedupe “última versão” em staging perde revisões antes do Vault | Preservar todas as observações distintas; resolver versão vigente no Business Vault |
| P0 | Raw Vault insert-only com fallback delete+insert é contraditório | Append idempotente no Raw Vault; correção por reconstrução/merge só em derivados |
| P0 | AUM somado no tempo e cotistas tratados como pessoas únicas | Contratos semânticos explícitos e oráculos independentes |
| P0 | Manifest de produção sem dados/relações acessíveis no CI | Fixture build completo; Slim CI só com baseline físico anexado e imutável |
| P1 | `dbt clone` considerado clone físico DuckDB | Fora de engines com zero-copy, é pointer view; não prova comportamento incremental |
| P1 | `fund × asset × month` pode colapsar posições legítimas | Chave documental/posição/bloco; consolidar por ativo apenas em modelo derivado |
| P1 | Hub de ativo universal pressupõe identificadores globais | Resolver identidade por bloco e sistema; manter posição não identificável |
| P1 | Hash concat_ws/upper aplicado indiscriminadamente | Serialização inequívoca, null distinto de vazio, normalização por domínio |
| P1 | Mudança histórica do gestor inferida do cadastro atual | Tempo observado separado de vigência efetiva; não inventar passado |
| P1 | Top10 como simples ratio sem universo/ranking definidos | Ranking por entidade/período; explicitar cobertura e restringir rollup |
| P1 | `avg_daily_return` confunde média e retorno acumulado | Métricas separadas, composição geométrica e elegibilidade definidas |
| P1 | D+2 como SLA garantido pela fonte | SLO local de ingestão e política de completude separados do atraso da fonte |
| P1 | `net_assets >= 0` e faixa de retorno arbitrária como falha universal | Alertas de domínio/quarentena contextual, não apagar fatos inesperados |
| P1 | Mudança só de métrica presumida selecionar SQL downstream | Executar regressão semântica explicitamente; seleção de modelos não basta |
| P2 | Versões v1/v2 de dimensão sem quebra real | Demonstrar versionamento em alteração concreta de contrato |
| P2 | Todos os marts públicos | Expor somente interfaces de consumo; `access` não é autorização de banco |
| P2 | Cinco packages e framework DV completo desde o início | Começar pequeno; adicionar cada dependência por necessidade comprovada |

O README atual de dbt-duckdb documenta merge e microbatch, mas microbatch faz delete+insert por janela e não usa `unique_key`. É inadequado como estratégia indiscriminada de Raw Vault imutável. Usá-lo em um derivado temporal opcional, com backfill fora do lookback testado. [Adapter](https://github.com/duckdb/dbt-duckdb).

AutomateDV e DataVault4dbt não listam DuckDB entre as plataformas oficialmente suportadas consultadas. Isso justifica avaliar SQL explícito e duas ou três macros pequenas; não justifica recriar todas as macros dessas bibliotecas. [AutomateDV](https://automate-dv.readthedocs.io/en/latest/platform_support/), [DataVault4dbt](https://github.com/ScalefreeCOM/datavault4dbt).

Referências de testes e CI: [clone](https://docs.getdbt.com/reference/commands/clone), [unit tests incrementais](https://docs.getdbt.com/docs/build/unit-tests), [semia aditividade — Kimball](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/).

## AI Analytics: o que a pesquisa sustenta

Spider 2.0 mostra que tarefas empresariais envolvem metadados, contexto do projeto e múltiplas etapas, muito além de traduzir uma frase para SQL. Seus resultados históricos não devem ser apresentados como ranking atual de modelos. BIRD acrescenta avaliação fundamentada no conteúdo das bases. [Spider 2.0](https://arxiv.org/abs/2411.07763), [BIRD](https://bird-bench.github.io/).

O benchmark público `dbt-llm-sl-bench` compara estratégias SQL, semantic layer e MCP. É uma referência útil para desenhar um experimento controlado, não prova de que nosso agente será correto. Fazer comparação A/B com o mesmo modelo, fixtures, perguntas e orçamento. [Benchmark dbt](https://github.com/dbt-labs/dbt-llm-sl-bench).

O blog oficial recente de context engineering reforça proveniência e contexto versionado. Seu package usa capacidades de warehouses e IA que não precisam entrar neste projeto. A ideia útil aqui é servir regras e evidências junto dos números; não adicionar embeddings e vector DB sem necessidade. [Context engineering](https://docs.getdbt.com/blog/dbt-context-engineering).

O MCP oficial inclui ferramentas locais e ferramentas de plataforma. Instalar o servidor não transforma automaticamente `query_metrics` em endpoint gratuito sobre DuckDB local. Descobrir toolsets e validar configuração; manter a interface de consulta local independente e pequena. [dbt MCP](https://github.com/dbt-labs/dbt-mcp).

## Limites da revisão

Confirmados: existência/acesso indicado no catálogo, fontes oficiais, campos dos dicionários, funcionalidades documentadas e metadados de dependências. Não confirmados: cardinalidade real, cobertura por classe/subclasse, qualidade de identificadores de ativos, histórico completo de revisões, performance, instalação conjunta e equivalência de resultados MetricFlow/DuckDB. Esses itens são gates explícitos do plano, não suposições resolvidas por documentação.
