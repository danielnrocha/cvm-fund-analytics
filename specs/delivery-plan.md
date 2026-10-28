# Plano de entregas e demonstração

> Stack aprovada pelo usuário em 28/10/2026: **dbt v2 + DuckDB + MetricFlow local**, sem serviços pagos obrigatórios. A primeira vertical mínima está implementada; a pipeline completa permanece pendente. Evidências e limites: [compatibilidade](compatibility.md) e [editor, linhagem e JSON](compatibility-extended.md).

**Estado:** execução autorizada e concluída apenas para a primeira vertical mínima; demais entregas continuam planejadas. A spec final de execução deverá incorporar os resultados dos gates de compatibilidade e profiling. Nenhuma versão de package ou grão ainda não testado é tratado como garantido.

**Objetivo:** pipeline local de fundos CVM com histórico verificável, métricas governadas e interface segura para AI BI.

## Organização futura

| Caminho proposto | Responsabilidade |
|---|---|
| `specs/` | Requisitos, design, ADRs, métricas e rastreabilidade |
| `extract/` | Download, hashes, manifests e ingestão operacional |
| `transform/` | Projeto dbt, modelos, macros, testes e documentação |
| `tests/fixtures/` | Dados sintéticos mínimos, casos de revisões e expected outputs |
| `tests/integration/` | Replay, correção tardia, rebuild e isolamento |
| `evals/` | Intenções, oráculos, holdout e traces da avaliação |
| `semantic_gateway/` | Interface pequena validada sobre MetricFlow local |
| `reviews/` | Findings e verificação independente por entrega |
| `.github/workflows/` | CI, UAT e release dentro da disponibilidade do plano |
| `.vscode/` | Interpreter, tarefas e extensões recomendadas |
| `data/`, `artifacts/` | Gerados, fora do Git; publicação somente por release manifest |

Não criar um framework de configuração novo. SQL+YAML dbt, `uv.lock`, manifests de dados e workflow YAML são suficientes. Só fixtures pequenas e sintéticas entram no Git por padrão; amostra real exige licença, atribuição e política de distribuição documentadas.

## Entrega 0 — stack aprovada e gates de compatibilidade

- [x] Decisão do usuário: dbt v2 + DuckDB + MetricFlow local; licença Apache integral não é requisito, ausência de serviço pago obrigatório é.
- [x] Resolver e fixar dois ambientes Python 3.12; versões e comandos em [compatibility.md](compatibility.md).
- [x] Build v2, manifesto novo, consultas mf e validação semântica locais, com rede bloqueada.
- [x] Incremental idempotente e correção de registro em fixture; não equivale à prova de Raw Vault append-only.
- [x] JSON externo com objetos, arrays, null, campo novo e registro malformado; preservar original e classificar rejeições em landing/staging.
- [x] VS Code: extensão ativada e tarefa de build real; diagnóstico SQL e painel avançado fora das garantias, conforme probe.
- [x] Análise estrita e arestas reais de linhagem de colunas em artefatos; docs geradas offline após bootstrap.
- [x] Unit test nativo com mutação real vermelho/verde; contrato de tabela bloqueia tipo e nome incompatíveis. [Evidências](compatibility-final-gates.md).
- [x] Semiaditividade em consultas reais: grãos diário/mensal/total, missing e última data comum vs última por conta; mutação da configuração detectada por oráculo. Não equivale à homologação do PL real.
- [x] Driver de docs Darwin-arm64 fixado por versão/tamanho/SHA-256; cópia local usada com cache global e rede bloqueados.
- [ ] Na entrega de CI: obter locks de driver por plataforma e hashes dos pacotes Python; validar bootstrap Linux em runner limpo.
- [x] CVM direta escolhida pelo usuário; recorte definido por profiling real: 60 classes, abril–setembro/2026. [Resultado](cvm-profiling.md).

O resultado específico de VS Code/LSP e a evidência da linhagem constam de [compatibility-extended.md](compatibility-extended.md). A baseline de apresentação usa tarefas VS Code e documentação estática local; recursos avançados da extensão só entram no roteiro com evidência de funcionamento. Wizard continua opcional.

Aceite: testes reproduzíveis com dois ambientes isolados e um banco local, sem rebuild Core para gerar o manifesto. Não exigir instalação conjunta nem confundir preparação com internet e execução offline. Gates técnicos do laptop concluídos; próximo passo é contrato/profiling de dados, não implementação automática da arquitetura inteira.

## Entrega 1 — contrato de dados e fixture de negócio

- [x] Inventariar recursos oficiais por catálogo; baixar dicionários e amostra delimitada, registrar hashes/licença.
- [x] Medir unicidade candidata, nulls, tipos, joins fundo–classe–subclasse, divergências e cobertura temporal.
- [x] Decidir a população em que PL e cotistas são economicamente disjuntos. Se impossível no escopo, restringir a coorte e documentar a exclusão.
- [x] Criar `specs/data-contracts.md` e `specs/metrics.md`; incluir fonte de cada regra e grain por tabela.
- [x] Criar e executar fixtures sintéticas de duplicatas, lacunas, identidade e fanout; TDD, mutações e revisão independente em [business-fixtures.md](business-fixtures.md).
- [ ] Completar fixtures de [ai-bi-evals.md](ai-bi-evals.md): unknown asset, CDA, parsing integral, replay persistente A→B→A e demais limites temporais. O probe A→B→A atual só valida separação de capturas em memória.

Profiling e contratos concluídos; fixtures dos quatro riscos executadas em laboratório isolado, demais fixtures e integração pendentes. [60 classes e 7.554 observações](cvm-profiling.md), seis lacunas e seis fechamentos reconciliados. A disjunção validada é hierárquica; participações cruzadas não foram consolidadas. Retornos e CDA continuam bloqueados.

Aceite: uma regra de seleção fixa identifica a amostra; um terceiro consegue calcular os golden totals manualmente. Nenhuma mudança cadastral ou revisão sintética é anunciada como evento real.

## Entrega 2 — ingestão e bronze com TDD

Implementado para a captura congelada: [landing imutável, envelope JSON e quarentena](ingestion.md), fontes físicas em lugar dos seeds, reconciliação por arquivo e gates. Aquisição genérica/agendada de capturas futuras continua pendente.

Arquivos: `extract/`, `tests/fixtures/`, `transform/models/staging/`, `transform/models/sources.yml`, testes de parsing.

- [ ] Escrever primeiro testes de envelope, arquivo truncado, schema desconhecido, null/vazio, encoding, precisão e arrays vazios.
- [x] Executar e observar falhas de envelope, imutabilidade, precisão, schema e gates antes das correções.
- [x] Implementar leitura mínima dos ZIPs CVM congelados, staging tipado, preservação de original e quarentena; sem downloader genérico.
- [x] Reexecutar regressões: oráculos PL/fluxo, MetricFlow, histórico e replay preservados.
- [x] Provar que reprocessar a mesma captura não duplica landing ou alteração de negócio; rede não integra esse teste.
- [x] Expor contagem por arquivo de aceitos, rejeitados e excluídos, reconciliada com manifest e profiling real.

Aceite: fixtures rodam sem rede e sem credenciais; erro na fonte não é convertido em sucesso silencioso. Freshness operacional e de conteúdo são distinguíveis.

## Entrega 3 — um caminho completo pelo Vault até AUM

**Fatia mínima executada:** [primeira vertical](first-vertical.md). Snapshot congelado por sources de landing JSON (substitui o seed tipado), identidade resolvida, satélite de capturas incremental, fato denso, PL/fluxo/cobertura no MetricFlow. Hubs/links e SCD2 cadastral não estão concluídos.

Arquivos: `transform/models/raw_vault/`, `business_vault/`, `marts/`, `transform/macros/` e `tests/integration/`.

- [ ] Escrever testes de hash, identidade hierárquica, duas versões no mesmo batch e correção antiga.
- [ ] Construir hubs/links/satélites mínimos do design; nenhuma macro genérica sem segunda necessidade real.
- [x] Satélite mínimo: testar replay, correção de data antiga e A→B→A; contagem/sequência histórica verificadas em projeto temporário.
- [ ] Construir dimensão com histórico de observação e `fct_entity_daily`; comprovar intervalos sem sobreposição. Cadastro atual só permite atributos `at_capture`, sem atribuição histórica retroativa; vigência de negócio exige fonte histórica adicional.
- [x] Comparar full rebuild com todas as capturas e incremental por deltas nas mesmas observações sintéticas; não usar full-refresh sobre delta incompleto.
- [x] Expor PL, net flow e cobertura no MetricFlow local: seis meses reais, total e filtro sobre lacuna reconciliados; corte não recua. Mutação da semiaditividade detectada.

Aceite: o cenário 330 → 335 funciona preservando consulta anterior, sem duplicação após replay. Nenhum dado de negócio é apagado no Raw Vault.

## Entrega 4 — carteira mensal e armadilhas de grão

- [ ] Modelar posições com grão documental validado; resolver ativo apenas onde existe identificador confiável.
- [ ] Adicionar cobertura e confidencialidade como dados de primeira classe.
- [ ] Testar que três posições de A e duas de B não multiplicam PL.
- [ ] Definir e provar concentração dos ativos divulgados; recusar consolidação fora do grão suportado.
- [ ] Demonstrar casts, arrays e blocos diferentes usando envelope explicitamente derivado.

Aceite: métricas apresentam população, competência e cobertura; carteira parcial não é apresentada como completa. Expandir para outros blocos requer novos contratos, não apenas aceitar novas colunas automaticamente.

## Entrega 5 — camada semântica e AI BI

- [ ] Completar catálogo de métricas e dimensões permitidas, com descrições e sinônimos PT/EN.
- [ ] Modelar time spine; validar ausência vs zero, fechamento comum vs último disponível e retorno composto.
- [ ] Executar `mf validate-configs` e queries reais; comparar todas as métricas publicadas com oráculos.
- [ ] Implementar contrato de ferramentas de leitura sobre MetricFlow. Nenhuma escrita/SQL livre como fallback.
- [ ] Rodar suíte determinística e, se houver modelo disponível, evals de intenção e narrativa com holdout.
- [ ] Demonstrar um gráfico alimentado somente pelos resultados validados, com unidade, período e cobertura.

Aceite: metas de [ai-bi-evals.md](ai-bi-evals.md) satisfeitas ou falhas explicitamente bloqueiam a publicação das capacidades afetadas. Um simples `mf query` é uma demo semântica, não demonstração de um agente já avaliado.

## Entrega 6 — CI, UAT e release

- [x] Bootstrap CI Linux ARM64: imagem e driver fixados, build, docs e runner completos aprovados offline em container local. [Evidência e limites](ci-uat.md).
- [ ] CI de PR: workflow e runner implementados com dois locks, full build estrito, unit/data tests, replay, rejeições, `mf validate-configs`, oráculos, mutação semântica e arestas de linhagem. Aceite Linux local aprovado; ativação remota pendente; lint de formatação SQL permanece separado.
- [x] Guardar artifacts e logs em workspaces exclusivos por release, com invocation ID registrado; baseline selado não é sobrescrito. Workflow preparado para publicar artefatos de cada run.
- [ ] Slim CI opcional: fixture baseline físico fechado + manifest correspondente; attach read-only; provar que nada escreve no baseline.
- [x] Gate semântico cobre mudança somente em métrica: mutação de semiaditividade bloqueada em teste real. Workflow não filtra caminhos e configura full build em toda execução; runner Linux local aprovado; execução do workflow no GitHub ainda pendente.
- [x] UAT local: comparação MetricFlow em total/mês/classe-dia/cobertura, mesmos inputs, null ≠ zero, schema obrigatório e relatório vinculado aos bundles/CAS. Provas positiva e negativa executadas; igualdade obrigatória antes da promoção.
- [ ] Aprovação humana antes da promoção; usar environments protegidos apenas se disponíveis. Caso contrário, documentar gate manual por release sem fingir proteção automatizada.
- [x] Empacotar snapshot consistente; testar promoção e rollback locais; registrar fingerprints de código/locks/dados. [Implementação e evidências](snapshot-publication.md).

Aceite: cada release é rastreável e recuperável. Tests de dados permanecem na publicação; unit tests podem ser excluídos do build prod-demo se já executados sobre o SHA exato. Manter dados publicados anteriores quando freshness ou qualidade bloquearem o candidato.

## Protocolo adversarial

Em cada entrega executada, um revisor independente recebe spec, diff, testes e evidências, sem o raciocínio do autor. Pode ser outro agente ou humano. Findings contêm severidade, cenário reproduzível, resultado esperado/observado e evidência. Bug de comportamento deve virar teste que falha; um risco de licença/custo/configuração pode exigir probe ou documentação em vez de teste artificial.

Autor corrige; revisor verifica. P0/P1 bloqueiam. P2 aceito exige justificativa e responsável. Revisão não é certificação de ausência de bugs; não usar ciclos infinitos de “assine até aprovar”. Após duas rodadas sem convergência, explicitar decisão pendente ao usuário. Não declarar “revisão independente aprovada” com base apenas na revisão do próprio autor.

Este pacote recebeu revisão de consistência pelo autor; **o laboratório de fixtures recebeu revisão independente**, documentada em [reviews/business-fixtures-review.md](../reviews/business-fixtures-review.md). A primeira vertical também recebeu [revisão independente](../reviews/first-vertical-review.md), com três achados corrigidos e revalidados. A [ingestão](../reviews/ingestion-review.md) também recebeu revisão independente com quatro achados corrigidos. Probes de compatibilidade não receberam revisão independente.

## Roteiro da apresentação

Não é realista criar do zero a arquitetura inteira do prompt em 20 minutos. Recomendo 45–60 minutos para workshop, ou uma apresentação de 20 minutos sobre projeto preparado com uma alteração pequena feita ao vivo.

| Tempo — versão 20 min | Mostrar | Comandos previstos, a validar no ensaio |
|---|---|---|
| 0–2 | Pergunta de negócio e erro de soma temporal | Consulta ingênua vs oráculo da fixture |
| 2–4 | DAG bronze → vault → estrela | `dbt ls`, `dbt docs generate`, `dbt docs serve` |
| 4–8 | Teste vermelho de revisão/duplicação e correção pequena | `dbt build --select +fct_entity_daily --target dev` |
| 8–11 | Histórico preservado e SQL da macro | `dbt compile --select sat_daily_report` + inspeção do SQL |
| 11–14 | Mesmo KPI em duas granularidades e semiaditividade | `mf query` sobre métricas aprovadas |
| 14–17 | Agente consulta e recusa investidores únicos/carteira oculta | Ferramentas semânticas com trace visível |
| 17–20 | Diff de regra, testes semânticos e UAT | Resultados de PR previamente preparado + mudança local |

Os comandos acima são roteiro proposto, não comandos já executados. A sintaxe completa de `mf query` e group-bys será congelada no ensaio com nomes reais retornados pelo catálogo. Não colocar comando impossível num README só para parecer completo.

Workshop: acrescentar `dbt debug`, `deps`, `parse`, `ls`, `compile`, `run`, `test`, `build`, `source freshness`, docs, seleção `+modelo`, `state:modified+` e `--defer`. Explicar diferenças entre run/test/build. Microbatch e `--event-time-start/--event-time-end` ficam em um derivado escolhido e comprovado; não executar contra qualquer tabela incremental. Snapshots nativos podem ser explicados comparativamente, sem duplicar desnecessariamente a historização já feita no Vault.

Momentos de impacto: correção tardia altera 330 para 335 mas preserva 330 “como conhecido antes”; adicionar carteira não multiplica patrimônio; o agente distingue data comum de last available; ele recusa uma pergunta impossível com evidência; uma mudança só em YAML é detectada pelo CI semântico.

## Critérios finais do material didático

- Clone limpo + setup + fixture demo funcionam sem serviços pagos.
- Ingestão real é comando separado, não dependência de rede durante o palco.
- Make targets e VS Code tasks têm uma única fonte de comandos, com `.venv-dbt/bin/dbt` e `.venv-mf/bin/mf` explícitos.
- Docs mostram linhagem de modelos e colunas produzida por análise estrita; testes conferem arestas esperadas. O painel da extensão não é substituto desses artefatos.
- Sessão ensaiada três vezes; tempo e memória medidos no laptop usado na apresentação.
- Fonte congelada, testes e artefatos de fallback disponíveis localmente.
- README distingue capacidade implementada, extensão opcional e limitações conhecidas.

## Publicação local concluída — 28/10/2026

[Spec de snapshots](snapshot-publication.md): 13 cenários Python de publicação, dois builds reais de 48 recursos, promoção/rollback com leitor fixado, isolamento dev/UAT e MetricFlow read-only com oráculos preservados. A construção usa workspace e artefatos próprios por ambiente/release. Revisão adversarial em [snapshots-review.md](../reviews/snapshots-review.md). Esse foi o aceite da publicação local. O incremento CI/UAT abaixo acrescenta Linux e comparação semântica; aprovação protegida remota continua pendente.

## CI/UAT — implementação e aceite separados

[Spec CI/UAT](ci-uat.md): **70 testes Python e 48 recursos dbt aprovados no Linux ARM64 offline**, docs v2 com 13 modelos/manifesto preservado, quatro arestas de linhagem, comparação real baseline/candidato, promoção/rollback, replay, rejeições e mutação semântica bloqueada. Oráculos preservados: PL `119385193058.06`, fluxo `4725910556.15`, 7.554/7.560 observações. [Resultado](../transform/evidence/ci/linux-acceptance/result.json). Dev/UAT locais continuam em `cvm-atomic-v2`; promoção ocorreu apenas no sandbox CI. **Ativação GitHub e transporte real entre runs pendentes** (repositório local sem remote). Próximo passo operacional: publicar o repositório e o baseline durável preparado, executar o primeiro CI normal e validar um PR. Hashes das distribuições Python continuam pendentes; os locks atuais fixam versões.

## Portfólio e baseline durável — 28/10/2026

- [x] Git inicializado em `main`; README de portfólio, atribuição de dados, contribuição e template de PR.
- [x] Desenvolvimento local sem Docker: Makefile e task VS Code; Docker apenas no runner remoto como padrão.
- [x] Baseline retirado da retenção de Actions: pacote versionado de Release, lock SHA-256, restauração segura e checksums internos.
- [x] Pacote Linux aprovado preparado e restaurado localmente; testes TDD de transporte executados.
- [x] Nome aprovado: `cvm-fund-analytics`; descrição/topics preparados e README em inglês com gate semântico em destaque e roadmap separado.
- [ ] Definir conta/remote e licença de código; publicar repositório e draft Release com o asset preparado, habilitar imutabilidade e publicar.
- [ ] Executar download real da Release e CI remoto normal, configurar proteção de `main` e só então adicionar badge de CI.

Contrato e comandos: [portfolio.md](portfolio.md). Retenção de logs/artefatos do CI permanece 14 dias; disponibilidade dos ZIPs CVM upstream é uma restrição separada. Preparação local não implica publicação remota.
