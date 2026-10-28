# Publicação atômica local de snapshots

Implementada em 28/10/2026 para o mesmo host/filesystem. Snapshot aqui é um bundle de release, não um `dbt snapshot` SCD. A construção completa acontece isoladamente; somente a troca do ponteiro de ambiente é atômica.

## Contrato

- `data/releases/work/{dev|uat}/{id}`: banco e projeto de trabalho exclusivos. IDs não podem ser reutilizados; falhas retêm diagnóstico e nunca promovem automaticamente.
- `snapshots/{id}`: cópia fechada do DuckDB, projeto dbt, manifest/run_results, evidências, logs, validação e SHA-256 de todos os arquivos. Arquivos ficam read-only; symlinks e WAL pendente são rejeitados.
- `environments/{dev|uat}/current.json`: ponteiros e históricos independentes. Um bundle validado pode ser promovido entre ambientes sem reconstrução.
- Publicação serializada por `flock`, comparação com `--expected` e `os.replace` do ponteiro. Arquivos e diretórios relevantes recebem `fsync`. Consumidores resolvem uma vez, verificam hashes e mantêm o caminho fixo durante a consulta.
- Rollback verifica e reponta para o bundle anterior; não executa SQL, ingestão ou rebuild. Bundles antigos permanecem disponíveis para leitores já abertos; não há coleta automática.

O builder executa ingestão congelada, `dbt build` estrito, oráculos reais, `mf validate-configs` e consultas semânticas. Confere o invocation ID dos artefatos e todos os status. A identidade das fontes é capturada antes da cópia, comparada com o projeto copiado e novamente ao fim. Remove `PYTHONOPTIMIZE` dos validadores para não desabilitar seus asserts.

## Evidências de aceite

- TDD: 8 testes inicialmente vermelhos, correções de revisão com 2 regressões vermelhas; suíte final com **13 cenários distintos**.
- Dois bundles reais: `cvm-ingestion-v1` construído em dev; `cvm-atomic-v2` em UAT, este último com `PYTHONOPTIMIZE=1` no pai. Ambos: **48 recursos dbt**, incluindo 12 unit tests, 23 testes de dados e 13 modelos.
- Promoção dev mantendo UAT na versão anterior; conexão DuckDB já aberta continua lendo 7.560 pares da versão fixada.
- Publicação UAT, rejeição de expectativa desatualizada, rollback ao caminho exato do bundle anterior e nova promoção.
- MetricFlow sobre o banco publicado, usando cópia temporária do projeto e `config_options.access_mode: READ_ONLY`: seis oráculos mensais, estoque final, fluxo total, lacuna sem backfill e cobertura. Escrita no banco é rejeitada e SHA-256 não muda.
- PL final: **119.385.193.058,06**; fluxo acumulado: **4.725.910.556,15**; observações: **7.554/7.560**. Ambos os ambientes terminam em `cvm-atomic-v2`.

Evidências: [resultados reais](../transform/evidence/releases/publication-results.json), [logs TDD/build](../transform/evidence/releases/), [driver do exercício real](../transform/evidence/releases/verify_publication.py) e [revisão independente](../reviews/snapshots-review.md). O driver preserva o exercício histórico anterior ao gate UAT; não deve ser repetido contra ambientes ativos nem usado como driver da política nova. Para reproduzir a política atual, usar ci/run.py conforme a spec CI/UAT.

A revisão independente revalidou as cinco correções e registrou PASS, incluindo provas de corrida na cópia, integridade de arquivos aninhados, ordem de fsync e remoção de PYTHONOPTIMIZE.

## Operação

Na raiz do projeto, `PY=compatibility/dbt-v2-metricflow/.venv-mf/bin/python`:

```sh
$PY scripts/snapshot.py build --environment dev --id demo-v3
$PY scripts/snapshot.py promote --environment dev --id demo-v3 --expected cvm-atomic-v2
$PY scripts/snapshot.py read --environment dev
$PY scripts/snapshot.py compare --environment uat --baseline cvm-atomic-v2 --id demo-v3
# Usar o caminho de relatório retornado:
$PY scripts/snapshot.py promote --environment uat --id demo-v3 --expected cvm-atomic-v2 --gate data/releases/gates/RELATORIO.json
$PY scripts/snapshot.py rollback --environment uat --expected demo-v3
```

Primeira publicação omite `--expected`; depois ele identifica obrigatoriamente a release corrente. Build e promoção são ações separadas: revisar evidências antes de promover. O comando `read` usa DuckDB read-only. Para MetricFlow, fixar o bundle uma vez, copiar seu projeto para workspace descartável e configurar o adapter com `config_options: {access_mode: READ_ONLY}` e o caminho absoluto do banco publicado; logs/CSVs ficam fora do bundle. O driver documenta esse procedimento executável.

## Limites explícitos

O proprietário local é confiável: permissões e hashes detectam corrupção acidental, não protegem contra administrador que reescreva banco, hashes ou `validation.json`. `seal` aceita a declaração do builder; não certifica candidatos arbitrários. A fingerprint detecta mudanças observadas durante a construção, não é uma sandbox contra edições maliciosas transitórias.

Não foi simulado desligamento físico; a durabilidade é sustentada pela ordem de fsync e revisão, com injeção de falha antes de replace. Falha após replace pode representar commit já realizado: reler o ponteiro antes de repetir. Não há coordenação distribuída/NFS nem promessa de atomicidade da ingestão e do build inteiro. O CAS compara a identidade atual, permitindo A→B→A; não detecta toda publicação intermediária.

CI Linux, aprovação protegida, diff automatizado de métricas entre versões e ensaio de apresentação permanecem pendentes. `transform/cvm_demo.duckdb` continua banco de desenvolvimento mutável e não deve ser servido como release.

## Gate UAT posterior

A [spec CI/UAT](ci-uat.md) passa a exigir comparação semântica explícita antes de toda promoção UAT, inclusive bootstrap declarado. Os resultados acima preservam o histórico da entrega de snapshots; a nova política substitui os exemplos antigos de promoção UAT sem `--gate`.
