# Ingestão CVM, landing e quarentena — 28/10/2026

Seeds removidos da vertical de produção. Os modelos agora leem `source('cvm_landing', ...)`. A entrada é o conjunto de ZIPs oficiais já capturados e fixados por SHA-256; o comando não baixa nem muda silenciosamente os arquivos. O objetivo desta entrega é tornar essa captura reproduzível e auditável, sem ampliar a população contratada.

## Fluxo implementado

1. `scripts/ingest_cvm.py` valida SHA-256 dos nove recursos do manifest de fontes e preserva bytes integrais em `data/landing/objects/<sha256>`. Também preserva manifest, população e calendário. Objetos são criados com publicação atômica por hard link e permissão somente leitura; objeto existente diferente gera erro, nunca overwrite. Não é proteção contra um administrador que altere o filesystem.
2. O parser lê os seis CSVs oficiais dentro dos ZIPs, em Latin-1 e com delimitador `;`. Rejeita ZIP inesperado/truncado, membro com caminho inseguro e cabeçalho obrigatório ausente/duplicado. O original já preservado permanece disponível quando a análise estrutural falha; a transação de banco não é iniciada.
3. Valores são preservados como strings no envelope JSON, sem casts financeiros em Python. Empty vira null; campos novos são preservados e recebem `unknown_columns`, exigindo revisão antes do consumo tipado. Linhas com largura inválida preservam também `raw_fields`.
4. Apenas a população de 60 classes é envelopada. Identificador inválido não é descartado como fora da coorte: gera envelope com motivo de rejeição. Registros identificáveis fora da coorte são contados; o ZIP integral conserva sua evidência. Não se afirma ter validado financeiramente os registros excluídos.
5. O registro de envelopes, captura, manifest por arquivo e configurações no DuckDB ocorre em transação. Replay reconhece a assinatura e confere envelopes já registrados; duplicata de source ID aborta o batch. Arquivos já preservados podem permanecer sem batch aceito, por desenho.
6. `bronze_classified` usa JSON seguro e valida lexicalmente valores antes do consumo tipado: precisão/escala, data/competência, CNPJ, campos obrigatórios e cotistas. PL negativo válido é preservado. `quarantine` retém payload original e motivo; staging contém apenas aceitos.
7. Dependências explícitas de staging para quarentena, auditoria e calendário fazem `dbt build` bloquear todos os descendentes de negócio. Quarentena materializa antes do bloqueio. A coluna nova e uma data válida fora do calendário congelado não podem passar silenciosamente.

## Contratos de entrada

| Relação de landing | Grão e finalidade |
|---|---|
| `raw_envelopes` | capture_id × source_id; payload VARCHAR com schema_version=1, data e error; competência em coluna própria |
| `captures` | capture_id único, timestamp com timezone; modelo normaliza explicitamente para UTC sem fuso para manter compatibilidade com o satélite anterior |
| `files` | captura × SHA-256; membro ZIP, quantidade envelopada e excluída |
| `registry_cohort` | População governada e classificação `at_capture`, derivadas do manifest já validado no profiling |
| `report_calendar` | Calendário governado congelado, não inferido da carga corrente |
| `batches` | Assinatura de manifest/população/calendário, para registro idempotente |

População e calendário continuam sendo artefatos versionáveis de contrato, carregados como tabelas de source; não são dbt seeds nem são recalculados a partir de cada carga. A ingestão geral de cadastro histórico, reenquadramentos e mudanças de hierarquia continua fora desta entrega.

`source_id = SHA-256:membro:linha_física_inicial`. O parser também calcula ordinal lógico e linha final; o identificador persistido usa a linha inicial. Teste de campo CSV com newline comprova que ordinal e linha física não são confundidos. O envelope e suas colunas de proveniência são uma representação derivada; a fonte CVM continua CSV/ZIP.

## Reconciliação e qualidade

`audit_ingestion_files` compara por **captura e arquivo**, usando a proveniência dos envelopes: quantidade declarada = aceitos + rejeitados. Soma ainda excluídos para o total lido. Um teste nativo prova que excesso em um arquivo e falta em outro não podem se cancelar. Arquivos desconhecidos na tabela de envelopes também falham no full join da auditoria.

No snapshot real, total reconciliado com o profiling anterior: **3.227.984 lidos = 7.554 aceitos + 0 rejeitados + 3.220.430 excluídos**. O total lido/excluído vem da enumeração do parser, não de um segundo parser universal independente; os ZIPs originais permitem auditoria posterior. A classificação não revalida payloads excluídos.

Quarentena bloqueia a publicação da captura inteira, não apenas a entidade inválida. Não há preenchimento por zero. Datas fora do calendário congelado também bloqueiam antes do satélite; atualizar esse calendário é uma decisão de contrato, não um side effect de ingestão.

## TDD e provas

Evidências em `transform/evidence/ingestion/`:

- `01-python-red.log` → `02-python-green.log`: landing, replay, corrupção, schema, envelope e exclusão.
- `04-native-red.log`: classificador incompleto falha em exemplos de JSON malformado, largura CSV, nulls, escala decimal e competência.
- `09-review-red.log` → `10-python-green.log`: novos campos, linhas físicas multilinha e corrupção de envelope registrado.
- `11-calendar-red.log`: perda de data fora do calendário e dependências de gates ainda incompletas; `14-gates-green.log` comprova bloqueios corrigidos.
- `13-file-reconcile-red.log`: duas divergências por arquivo antes da correção.
- `15-history.log`: replay, A→B→A e equivalência incremental/rebuild continuam passando com fontes, sem seeds.
- `clean-results.json`: banco vazio, ingestão, replay, dbt build, reconciliação e oráculos MetricFlow passam.

O primeiro teste em banco vazio também detectou incompatibilidade entre o formato padrão criado pelo Python DuckDB 2.0 e o engine 1.5 embarcado no dbt v2. O writer agora fixa `storage_compatibility_version='v1.4.0'`, conforme [documentação oficial de armazenamento](https://duckdb.org/docs/current/internals/storage). A prova é o build real sobre banco novo, não somente a aceitação da configuração.

[Parecer adversarial independente](../reviews/ingestion-review.md): quatro achados corrigidos e revalidados. Testes independentes confirmaram que coluna nova, divergência do calendário e contagem por arquivo preservam satélite/corrente/fato anteriores; quarentena fica disponível.

## Limites mantidos

O comando é para recursos oficiais congelados, não um agendador genérico de aquisições. Arquivos fonte são imutáveis; tabelas DuckDB são projeções controladas pela aplicação, não um storage WORM protegido contra edição externa. Replay verifica envelopes, mas não é auditoria de integridade de cada tabela de metadados contra mudanças externas. Builds e promoção de release ainda não formam uma transação única: landing e intermediários podem evoluir antes de um gate falhar. Nunca servir o banco de trabalho como publicação atômica.

Capturas futuras exigem preservar todas as versões para rebuild. `dbt run` não substitui `dbt build`. JSON externo via reader direto continua fora do caminho: usamos tabela física com payload VARCHAR, compatível com o gate já validado. CI/Linux permanece pendente. A publicação local dev/UAT e o rollback foram implementados na [spec de snapshots](snapshot-publication.md).

## Aceite final

**13 testes Python, 12 unit tests nativos e 23 testes de dados passaram.** Build final: 48 recursos, incluindo 13 modelos, sem seeds, com análise estrita e rede bloqueada (`22-final-offline-build.log`). MetricFlow e os seis oráculos reais também passaram offline (`23-final-offline-mf.log`, `24-final-oracles.log`). O aviso de ausência de `dbt_cloud.yml` é o mesmo da vertical anterior; a validação semântica local é feita pelo MetricFlow.

A conversão de captura usa `make_timestamp(epoch_us(captured_at))`, preservando UTC e microssegundos sem depender do fuso da sessão. O teste nativo cobre offsets diferentes; o revisor confirmou a expressão em sessões UTC, São Paulo e Tóquio.
