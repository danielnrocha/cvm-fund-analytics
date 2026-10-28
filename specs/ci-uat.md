# CI Linux e comparação semântica para UAT

Estado em 28/10/2026: gate UAT implementado e runner Linux ARM64 aprovado em container local com `--network none`. Workflow GitHub ativado no repositório público `danielnrocha/cvm-fund-analytics`; consultar o histórico remoto para o estado atual dos runs.

## Gate antes da promoção

`release/uat.py` executa MetricFlow novamente contra baseline e candidato selados. Cada consulta usa uma cópia temporária do projeto e um perfil apontando ao banco publicado com `access_mode: READ_ONLY`. Nenhum CSV/log é escrito no bundle.

O conjunto de consultas compara:

| Grão | Métricas / finalidade |
|---|---|
| Total | PL final, fluxo acumulado, observações e entidades esperadas/reportadas |
| Mês | Mesmas seis métricas; detecta compensações entre períodos |
| Classe/dia | Mesmas métricas; detecta fanout, transferências entre identidades e lacunas |
| Mês | Cobertura do período e do fechamento |

Comparação por chave, independente da ordem; números normalizados com Decimal; tolerância zero. Null permanece diferente de zero. Coluna ausente, métrica inesperada, chave duplicada, grupo removido, resultado vazio e NaN/Infinity bloqueiam o gate. Cabeçalhos devem coincidir com as métricas solicitadas, inclusive quando ambos os lados omitirem a mesma métrica.

Baseline e candidato precisam dos mesmos hashes de `sources.json`, população, calendário e oráculos mensais. Mudanças nos dados congelados exigem recertificação explícita; não há aprovação automática por tolerância. O relatório guarda resultados completos, diferenças, especificação das consultas e hashes dos manifests de bundle. A promoção UAT confere tudo novamente sob o lock e vincula o relatório ao par exato de releases e ao valor esperado do ponteiro. Editar apenas `passed` não libera diferenças.

## Comandos locais

Na raiz, usando `PY=compatibility/dbt-v2-metricflow/.venv-mf/bin/python`:

```sh
$PY scripts/snapshot.py build --environment dev --id candidato-v3
$PY scripts/snapshot.py compare --environment uat --baseline cvm-atomic-v2 --id candidato-v3
# Inspecionar o JSON no caminho impresso; promover somente depois do aceite:
$PY scripts/snapshot.py promote --environment uat --id candidato-v3 --expected cvm-atomic-v2 --gate data/releases/gates/RELATORIO.json
$PY scripts/snapshot.py rollback --environment uat --expected candidato-v3
```

Primeira publicação UAT exige `compare --bootstrap --baseline ID --id ID` e o relatório correspondente; é certificação inicial sem comparação histórica. Não é um fallback automático quando falta baseline. Rollback continua voltando a um bundle histórico verificado; o gate novo se aplica à promoção.

O comando `compare` retorna status não zero para divergência e preserva o relatório. Falha no MF ou identidade de inputs incompatível também impede promoção. Não há override de diferenças neste incremento: mudanças intencionais de definição exigem novo contrato/oráculo revisado, fora do fluxo de igualdade.

## CI executável

`ci/Dockerfile` fixa a imagem-base por digest e instala os dois locks Python separadamente. O workflow `.github/workflows/linux-ci.yml` usa Linux ARM64 (`ubuntu-24.04-arm`), com actions fixadas por SHA. Bootstrap online instala dependências, prepara driver Linux e adquire os bytes CVM fixados. Cache é uma otimização: todo arquivo restaurado é validado por tamanho e SHA-256; drift na origem falha sem atualizar `sources.json`.

O processo de aceite roda em `docker run --network none`, com os arquivos fonte montados read-only. Executa testes Python, build dbt completo/estrito, oráculos reais, MetricFlow, driver de docs, linhagem de colunas, comparação semântica, promoção/rollback isolados, mutação semiaditiva, replay e rejeições de dados. Relatórios do gate e saídas da comparação ficam fora dos bundles; logs do build e validation.json integram o bundle selado. Workspaces são exclusivos por release.

O CI não publica nos ambientes locais de Daniel. Seus ponteiros são descartáveis e demonstram a política. O artefato `cvm-release` contém evidências e bundles; aprovação e promoção reais usam o CLI no release root escolhido.

### Baseline no GitHub

Decisão de portfólio: GitHub Actions + Docker no runner remoto; desenvolvimento local sem Docker. O [runbook de publicação](portfolio.md) substitui o mecanismo anterior de baseline por run ID.

`ci/baseline.lock.json` fixa tag, asset, snapshot ID, tamanho e SHA-256 de uma GitHub Release. `ci/baseline.py fetch` baixa o asset público, verifica hash e estrutura e restaura todos os membros do bundle em `baseline/releases`. Nenhum baseline depende mais de `CVM_BASELINE_RUN_ID`, variáveis de repositório ou expiração de Actions artifacts. Os artefatos do run continuam com retenção de 14 dias apenas para diagnóstico.

O pacote real `dist/cvm-baseline-v1.zip` foi publicado em `baseline-v1` com imutabilidade habilitada e download público verificado. O primeiro CI normal exige esse asset publicado. Bootstrap manual é explícito e não altera a seleção aprovada. Para substituir o baseline, revisar um novo bundle e publicar uma nova tag/asset com lock correspondente; não sobrescrever a release. Release immutability está habilitada; proteção/revisão obrigatória de `main` continua pendente.

Runners padrão em repositório público não exigem serviços dbt pagos; limites de armazenamento e governança do GitHub continuam aplicáveis. [Documentação dos runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). O isolamento do container remoto continua sendo `--network none`. Executar o container no Mac é opção excepcional de diagnóstico, não o fluxo normal.

## Fronteiras

- O proprietário do filesystem, o código de validação e a escolha humana do baseline são confiáveis. Hashes não são assinatura, ACL ou aprovação protegida.
- Um autor com poder de mudar o próprio workflow pode alterar os gates: branch protection/review humano continuam necessários para governança real. Nenhuma proteção remota foi configurada aqui.
- Não reivindicamos validação amd64: a emulação local falhou ao importar DuckDB Python com SIGILL. O alvo previsto deste incremento é Linux ARM64.
- Locks Python fixam versões; ainda não fixam hashes de todas as distribuições. Driver e imagem-base têm hashes próprios.
- Comparação cobre o conjunto explícito de métricas/grãos, não todas as perguntas possíveis de BI. Fonte externa nova e mudança intencional de métrica exigem novo aceite.
- CI sempre faz full build. Slim CI e lint de formatação SQL são melhorias futuras; parsing/análise estrita e testes de negócio são obrigatórios.

## Evidência de aceite

- macOS e Linux ARM64: 29 testes release/UAT, 15 testes CI, 13 de ingestão e 13 de negócio passaram (70 no total). As primeiras versões dos gates de comparação, download, driver e linhagem tiveram falhas registradas antes das correções.
- Comparação real `cvm-ingestion-v1` → `cvm-atomic-v2`: quatro consultas por lado, sem diferenças, incluindo classe/dia.
- Mutação real: remover a semiaditividade altera o PL nos seis meses e no total; promoção é rejeitada e ponteiro permanece byte a byte igual. [Resultado](../transform/evidence/ci/semantic-mutation.json).
- Driver Linux ARM64 obtido diretamente do CDN oficial: 86.705.784 bytes, SHA-256 `344d183eaaf97255b49a1a084497999a50989397444fe4aaf44bbbca19b66917`. O lock também fixa os bytes comprimidos. Bootstrap usa libzstd do sistema, limites de tamanho e ambos os hashes; não precisa executar o driver para prepará-lo. [Lock](../ci/docs-driver-linux.lock.json), [download verificado](../transform/evidence/ci/driver-download.json), [formato do URL no código oficial](https://github.com/dbt-labs/dbt-core/blob/main/crates/dbt-adbc/src/install.rs). Download e identificação ELF não comprovam execução da biblioteca.
- Linux amd64 emulado: DuckDB Python termina com SIGILL; não é homologação de runner amd64 nativo.
- Linux ARM64: execução completa offline **aprovada** em container local Linux/aarch64: 48 recursos dbt (13 modelos, 12 unit tests, 23 data tests), 70 testes Python, oráculos, MetricFlow, quatro arestas de linhagem, docs, comparação baseline/candidato, promoção/rollback, mutação, replay e rejeições. [Resultado](../transform/evidence/ci/linux-acceptance/result.json).
- Docs v2: HTML + `info_schema/v1/dbt.models.parquet`, 13 modelos, manifesto preservado. Não exigir o antigo `catalog.json`. Driver fixado atende todos os comandos pelo `ADBC_DRIVER_PATH` do container. [Evidência](../transform/evidence/ci/linux-acceptance/docs.log).
- Comparação Linux `cvm-atomic-v2` → `cvm-linux-uat-v3`: zero diferenças. [Relatório completo](../transform/evidence/ci/linux-acceptance/semantic-comparison.json). Mutação de semiaditividade rejeitada (seis meses e total), ponteiro intacto. [Resultado](../transform/evidence/ci/linux-acceptance/semantic-mutation.json).
- A falha inicial de extração por I/O foi superada após liberar espaço. A execução offline revelou e corrigiu duas regressões: driver não exposto ao build e verificador de docs legado. Logs de falhas e testes red/green permanecem em `transform/evidence/ci/`.
- Os ambientes locais publicados permanecem em `cvm-atomic-v2`. O CI está ativado no GitHub; o primeiro run identificou a dependência de diretório vazio nos testes auxiliares, corrigida e documentada no runbook de portfólio.

Para reproduzir o aceite local, usar saída e ID novos no comando abaixo. O aceite prova o container Linux ARM64 local; a publicação remota e o download real da Release estão documentados no [runbook](portfolio.md). Hashes completos das distribuições Python permanecem como melhoria explícita, sem confundir os locks de versão atuais com locks por hash.

```sh
docker build --platform linux/arm64 -f ci/Dockerfile -t cvm-ci:run .
mkdir -p ci-output
docker run --rm --platform linux/arm64 --network none \
  -v "$PWD/profiling/cvm/raw:/workspace/profiling/cvm/raw:ro" \
  -v "$PWD/data/releases:/baseline:ro" \
  -v "$PWD/ci-output:/results" \
  cvm-ci:run /opt/venv-mf/bin/python ci/run.py \
  --output /results --id cvm-linux-uat-v1 \
  --baseline-root /baseline --baseline-id cvm-atomic-v2
```

Usar outro ID/diretório de saída se uma tentativa já criou o workspace desse ID. A comparação não exige que o baseline tenha sido construído no mesmo SO: ambos são consultados pelo mesmo runtime MetricFlow do gate.

O transporte do baseline inclui arquivos ocultos (`include-hidden-files: true`): eles constam do manifesto selado. O teste `tests/ci/test_transport.py` reproduziu checksum inválido antes da correção e verifica ida e volta ZIP com a seleção configurada no workflow. É uma simulação local do transporte, não evidência de execução da action no GitHub.
