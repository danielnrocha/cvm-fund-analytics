# Plano de entregas e demonstração

> Stack aprovada pelo usuário em 28/10/2026: **dbt v2 + DuckDB + MetricFlow local**, sem serviços pagos obrigatórios. A primeira vertical mínima está implementada; a pipeline completa permanece pendente. Evidências e limites: [compatibilidade](compatibility.md) e [editor, linhagem e JSON](compatibility-extended.md).

**Estado atual:** vertical CVM, ingestão congelada, histórico mínimo, PL/fluxo/cobertura, publicação atômica, CI remoto e proteção de main implementados. A prioridade atual é a [demo prática de 20–25 minutos](live-demo.md). Vault completo, carteira, retornos e agente continuam no roadmap. Checklists históricos abaixo não são pré-requisitos adicionais para apresentar a vertical existente.

**Objetivo:** pipeline local de fundos CVM com histórico verificável, métricas governadas e interface segura para AI BI.

## Organização de referência (implementada parcialmente)

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

Aceite: testes reproduzíveis com dois ambientes isolados e um banco local, sem rebuild Core para gerar o manifesto. Não exigir instalação conjunta nem confundir preparação com internet e execução offline. Gates técnicos e profiling concluídos; a entrega atual é preparar e ensaiar a apresentação da vertical implementada.

## Entrega 1 — contrato de dados e fixture de negócio

- [x] Inventariar recursos oficiais por catálogo; baixar dicionários e amostra delimitada, registrar hashes/licença.
- [x] Medir unicidade candidata, nulls, tipos, joins fundo–classe–subclasse, divergências e cobertura temporal.
- [x] Decidir a população em que PL e cotistas são economicamente disjuntos. Se impossível no escopo, restringir a coorte e documentar a exclusão.
- [x] Criar `specs/data-contracts.md` e `specs/metrics.md`; incluir fonte de cada regra e grain por tabela.
- [x] Criar e executar fixtures sintéticas de duplicatas, lacunas, identidade e fanout; TDD, mutações e revisão independente em [business-fixtures.md](business-fixtures.md).
- [ ] Completar fixtures futuras de [ai-bi-evals.md](ai-bi-evals.md): unknown asset, CDA, parsing integral e demais limites temporais. A→B→A persistente, replay e rebuild já são cobertos por `scripts/check_history.py`; cenários de CDA/ativos continuam fora da vertical.

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
- [x] Time spine, ausência vs zero e fechamento comum implementados para PL/fluxo/cobertura.
- [ ] Retorno composto e produto de consulta latest-available continuam fora desta entrega.
- [x] Executar `mf validate-configs` e queries reais para as métricas publicadas da vertical; demais métricas exigem novos oráculos.
- [ ] Implementar contrato de ferramentas de leitura sobre MetricFlow. Nenhuma escrita/SQL livre como fallback.
- [ ] Rodar suíte determinística e, se houver modelo disponível, evals de intenção e narrativa com holdout.
- [ ] Demonstrar um gráfico alimentado somente pelos resultados validados, com unidade, período e cobertura.

Aceite: metas de [ai-bi-evals.md](ai-bi-evals.md) satisfeitas ou falhas explicitamente bloqueiam a publicação das capacidades afetadas. Um simples `mf query` é uma demo semântica, não demonstração de um agente já avaliado.

## Entrega 6 — CI, UAT e release

- [x] Bootstrap CI Linux ARM64: imagem e driver fixados, build, docs e runner completos aprovados offline em container local. [Evidência e limites](ci-uat.md).
- [x] CI de PR: workflow e runner implementados com dois locks, full build estrito, unit/data tests, replay, rejeições, `mf validate-configs`, oráculos, mutação semântica e arestas de linhagem. Aceite Linux local aprovado; ativação remota executada; lint de formatação SQL permanece separado.
- [x] Guardar artifacts e logs em workspaces exclusivos por release, com invocation ID registrado; baseline selado não é sobrescrito. Workflow preparado para publicar artefatos de cada run.
- [ ] Slim CI opcional: fixture baseline físico fechado + manifest correspondente; attach read-only; provar que nada escreve no baseline.
- [x] Gate semântico cobre mudança somente em métrica: mutação de semiaditividade bloqueada em teste real. Workflow não filtra caminhos e configura full build em toda execução; runner Linux local aprovado; execução remota comprovada, incluindo rejeição de regressão diária no PR #1.
- [x] UAT local: comparação MetricFlow em total/mês/classe-dia/cobertura, mesmos inputs, null ≠ zero, schema obrigatório e relatório vinculado aos bundles/CAS. Provas positiva e negativa executadas; igualdade obrigatória antes da promoção.
- [ ] Aprovação humana antes da promoção; usar environments protegidos apenas se disponíveis. Caso contrário, documentar gate manual por release sem fingir proteção automatizada.
- [x] Empacotar snapshot consistente; testar promoção e rollback locais; registrar fingerprints de código/locks/dados. [Implementação e evidências](snapshot-publication.md).

Aceite: cada release é rastreável e recuperável. Tests de dados permanecem na publicação; unit tests podem ser excluídos do build prod-demo se já executados sobre o SHA exato. Manter dados publicados anteriores quando freshness ou qualidade bloquearem o candidato.

## Protocolo adversarial

Em cada entrega executada, um revisor independente recebe spec, diff, testes e evidências, sem o raciocínio do autor. Pode ser outro agente ou humano. Findings contêm severidade, cenário reproduzível, resultado esperado/observado e evidência. Bug de comportamento deve virar teste que falha; um risco de licença/custo/configuração pode exigir probe ou documentação em vez de teste artificial.

Autor corrige; revisor verifica. P0/P1 bloqueiam. P2 aceito exige justificativa e responsável. Revisão não é certificação de ausência de bugs; não usar ciclos infinitos de “assine até aprovar”. Após duas rodadas sem convergência, explicitar decisão pendente ao usuário. Não declarar “revisão independente aprovada” com base apenas na revisão do próprio autor.

Este pacote recebeu revisão de consistência pelo autor; **o laboratório de fixtures recebeu revisão independente**, documentada em [reviews/business-fixtures-review.md](../reviews/business-fixtures-review.md). A primeira vertical também recebeu [revisão independente](../reviews/first-vertical-review.md), com três achados corrigidos e revalidados. A [ingestão](../reviews/ingestion-review.md) também recebeu revisão independente com quatro achados corrigidos. Probes de compatibilidade não receberam revisão independente.

## Roteiro da apresentação — escopo atual

O [runbook executável](../demo/RUNBOOK.md) substitui o roteiro especulativo anterior. Demo sobre projeto preparado, não construção completa do zero.

| Tempo | Mostrar | Implementação real |
|---|---|---|
| 0–3 | PL de fechamento, fluxo e cobertura | MetricFlow sobre 60 classes e seis meses |
| 3–6 | Fonte, modelo, contrato e linhagem | `dbt ls`, `compile`, docs e `fct_daily` |
| 6–11 | Ausência convertida indevidamente em zero | Unit test nativo vermelho/verde |
| 11–18 | SQL válido com PL agregado incorretamente | Mutação YAML, consulta real e oráculo vermelho/verde |
| 18–22 | Totais iguais escondem regressão diária | Evidência do PR #1 e gate que bloqueou merge/promoção |
| 22–25 | Histórico e perguntas | Satélite existente; limites da demo |

Preparação/reset: `make demo-prepare` e `make demo-reset`. Ensaio automatizado: `bash demo/rehearse.sh`. Comandos individuais permanecem visíveis no roteiro; não usar o script inteiro como apresentação. Agente, carteira, microbatch e Slim CI não fazem parte desta sessão. Não prometer painel avançado da extensão VS Code.

## Critérios finais do material didático

- Clone limpo + setup + fixture demo funcionam sem serviços pagos.
- Ingestão real é comando separado, não dependência de rede durante o palco.
- Make targets e VS Code tasks têm uma única fonte de comandos, com `.venv-dbt/bin/dbt` e `.venv-mf/bin/mf` explícitos.
- Docs mostram linhagem de modelos e colunas produzida por análise estrita; testes conferem arestas esperadas. O painel da extensão não é substituto desses artefatos.
- Sequência técnica ensaiada três vezes com rede bloqueada; tempo/memória registrados. O ensaio falado de 20–25 minutos pelo apresentador é um aceite distinto e ainda necessário.
- Fonte congelada, testes e artefatos de fallback disponíveis localmente.
- README distingue capacidade implementada, extensão opcional e limitações conhecidas.

## Publicação local concluída — 28/10/2026

[Spec de snapshots](snapshot-publication.md): 13 cenários Python de publicação, dois builds reais de 48 recursos, promoção/rollback com leitor fixado, isolamento dev/UAT e MetricFlow read-only com oráculos preservados. A construção usa workspace e artefatos próprios por ambiente/release. Revisão adversarial em [snapshots-review.md](../reviews/snapshots-review.md). Esse foi o aceite da publicação local. O incremento CI/UAT abaixo acrescenta Linux e comparação semântica; proteção remota de merge implementada posteriormente em [main-protection.md](main-protection.md); aprovação humana de promoção permanece uma política separada.

## CI/UAT — implementação e aceite separados

[Spec CI/UAT](ci-uat.md): **70 testes Python e 48 recursos dbt aprovados no Linux ARM64 offline**, docs v2 com 13 modelos/manifesto preservado, quatro arestas de linhagem, comparação real baseline/candidato, promoção/rollback, replay, rejeições e mutação semântica bloqueada. Oráculos preservados: PL `119385193058.06`, fluxo `4725910556.15`, 7.554/7.560 observações. [Resultado](../transform/evidence/ci/linux-acceptance/result.json). Dev/UAT locais continuam em `cvm-atomic-v2`; promoção ocorreu apenas no sandbox CI. **Publicação GitHub e download da Release executados.** O histórico remoto registra o CI atual; proteção de `main` aplicada e regressão semântica bloqueada no PR #1; ver [aceite de PR](main-protection.md). Hashes das distribuições Python continuam pendentes; os locks atuais fixam versões.

## Portfólio e baseline durável — 28/10/2026

- [x] Git inicializado em `main`; README de portfólio, atribuição de dados, contribuição e template de PR.
- [x] Desenvolvimento local sem Docker: Makefile e task VS Code; Docker apenas no runner remoto como padrão.
- [x] Baseline retirado da retenção de Actions: pacote versionado de Release, lock SHA-256, restauração segura e checksums internos.
- [x] Pacote Linux aprovado preparado e restaurado localmente; testes TDD de transporte executados.
- [x] Nome aprovado: `cvm-fund-analytics`; descrição/topics preparados e README em inglês com gate semântico em destaque e roadmap separado.
- [x] Repositório público `danielnrocha/cvm-fund-analytics`, metadados aplicados, baseline publicado com imutabilidade e download público verificado.
- [ ] Selecionar licença de código (publicação pública não concede licença automaticamente).
- [x] Executar download real da Release e iniciar CI remoto normal; primeiro run revelou dependência de pasta vazia, corrigida nos testes auxiliares.
- [x] Configurar proteção de `main` e comprovar bloqueio de regressão semântica no PR #1; aceite da revisão final e pós-merge acompanhado no histórico remoto ([política e evidências](main-protection.md)).

Contrato e comandos: [portfolio.md](portfolio.md). Retenção de logs/artefatos do CI permanece 14 dias; disponibilidade dos ZIPs CVM upstream é uma restrição separada. Preparação local não implica publicação remota.

Publicação executada em 28/10/2026: [repositório](https://github.com/danielnrocha/cvm-fund-analytics), [baseline imutável](https://github.com/danielnrocha/cvm-fund-analytics/releases/tag/baseline-v1), [CI remoto](https://github.com/danielnrocha/cvm-fund-analytics/actions/workflows/linux-ci.yml). Histórico de preparação acima permanece datado; publicação e download não estão mais pendentes.

## Preparação da demo — entrega atual

- [x] Spec delimitada e roteiro com os comandos reais do projeto: [live-demo.md](live-demo.md).
- [x] Ambiente descartável a partir de baseline local verificado; perfil exclusivo e reset com identificação de propriedade.
- [x] Testes de ciclo de vida escritos antes da implementação; negativos de negócio executados com dbt/MetricFlow reais.
- [x] Descrições de grão, unidades, captura, ausência e semiaditividade no YAML.
- [x] Driver de docs local fixado usado também no Makefile e no roteiro.
- [x] Três ensaios técnicos aprovados com rede bloqueada (23,78 / 21,81 / 22,15 s), revisão adversarial sem bloqueadores e [aceite consolidado](../demo/evidence/acceptance.json). Linhagem de modelos e colunas inspecionada no navegador integrado.
- [ ] Apresentador ensaiar a fala e navegação em 20–25 minutos, usando o notebook da sessão.

Nada nesta entrega publica nova baseline, promove dev/UAT ou transforma o roadmap de AI BI/Vault completo em capacidade implementada.
