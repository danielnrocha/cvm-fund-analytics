# Prova de compatibilidade — dbt v2 + DuckDB + MetricFlow

Escopo: fixtures sintéticas de quatro remessas, dois saldos por entidade ao longo do tempo e JSON externo; não implementa o projeto da demo.
Requisito confirmado pelo usuário: execução sem serviços pagos; licença Apache 2.0 não é obrigatória.

## Reprodução no macOS

Requer Python 3.12, `uv` e `/usr/bin/sandbox-exec`. Executar nesta pasta:

```sh
uv venv --python 3.12 .venv-dbt
uv pip install --python .venv-dbt/bin/python -r requirements-dbt.lock
uv venv --python 3.12 .venv-mf
uv pip install --python .venv-mf/bin/python -r requirements-mf.lock
# Preparar driver adicional usado pela geração da documentação (acesso à internet):
.venv-mf/bin/python load_json_fixture.py
DBT_SEND_ANONYMOUS_USAGE_STATS=false .venv-dbt/bin/dbt build --profiles-dir .
.venv-mf/bin/python pinned_docs.py --bootstrap
# A partir daqui, cada processo de teste roda com rede bloqueada:
.venv-mf/bin/python run_probe.py
.venv-mf/bin/python verify_extended.py
.venv-mf/bin/python run_remaining_gates.py
```

Os locks fixam versões Python, sem hashes de distribuição. O driver de documentação tem lock próprio em `docs-driver.lock.json` (versão, plataforma, tamanho e SHA-256). `pinned_docs.py` verifica a cópia local e recusa drift; não aplica esse driver às transformações. O hash é do artefato observado no download oficial, não uma assinatura do fornecedor. A reprodução Linux requer driver e hash próprios, além de substituir o bloqueio de rede específico do macOS. O wrapper recusa plataformas não homologadas.

## Fronteira entre motores

- `.venv-dbt/bin/dbt`: dbt 2.0.9; único motor que faz build/parse dos modelos nesta prova.
- `.venv-mf/bin/mf`: dbt-metricflow 0.15.0 / MetricFlow 0.213.0; usa o adapter Python DuckDB 1.11.1 e DuckDB Python 2.0.0.
- O pacote MetricFlow instala dbt-core 1.12.6 como dependência e chama internamente `dbtRunner debug` para carregar configuração/conexão. Não se trata de uma instalação sem Core Python.
- Não executamos build/parse Core para produzir o manifesto. O hash do manifesto é conferido antes e depois das consultas MetricFlow.
- O driver embutido utilizado pelo build v2 reportou DuckDB v1.5.4. Não confundir com a versão do pacote Python.
- Não há configuração de conta, token, warehouse remoto ou `dbt sl` no teste. Instalação e preparo de dependências precisam de internet; execução principal é testada sem rede.

## O que o teste verifica

Build, três data tests, extração JSON aninhado e campo ausente, incremental `delete+insert`, idempotência, correção de registro, manifesto semântico na nova sintaxe YAML, validação semântica e de banco, cinco consultas com oráculos numéricos, SQL gerado, rejeição de métrica/dimensão inexistente e geração da documentação.

A fixture produz receita 1.000, custo 600, quatro remessas e margem 40%. Janeiro tem margem 1/3: a média incorreta das margens por remessa seria 1/3 nesse mês por coincidência dos dados, mas a margem global correta é 40%, diferente da média por remessa (37,5%). Os oráculos verificam os valores exatos por granularidade.

`evidence/results.json` e `evidence/run-summary.log` contêm os resultados finais; logs 01–04 documentam as tentativas iniciais. A sintaxe antiga não produziu o manifesto necessário para mf. `16-docs-before-driver.log` registra a falha offline antes de preparar o driver; `17-docs-driver-download.log` registra o preparo online.

Limites: fonte CVM/BD, escala, concorrência de escrita, joins entre fatos, snapshots e CI Linux não foram homologados. Contratos testados são de nome/tipo em tabela; constraints físicas e contratos incrementais não são garantidos por essa prova. Não equivale à homologação da arquitetura inteira.

## Validação complementar

`verify_extended.py` reproduz a falha esperada de read_json direto com análise estrita, comprova leitura runtime e testa a alternativa aprovada: arquivo JSONL → landing física preservada → staging SQL. São 14 asserções de dados/linhagem, mais os controles de leitura direta. O arquivo contém um registro malformado propositalmente; a versão `external-valid.jsonl` serve ao probe de read_json. A captura com checksum é sintética e não implementa o extrator CVM.

A prova de VS Code está em `../vscode-probe-extension/`; `evidence/25-vscode.json` registra versão, ativação e resultado da tarefa executada no extension host real. O perfil e a extensão foram instalados somente em `../vscode-sandbox/`, sem modificar extensões do perfil habitual. `.vscode/tasks.json` permite repetir build, compile estrito, docs e consultas locais. Abra esta pasta como raiz do workspace.

A validação complementar substitui os limites iniciais sobre JSON externo, análise estrita e execução básica no VS Code. O relatório canônico é [compatibility-extended.md](../../specs/compatibility-extended.md). Consulte-o antes de anunciar funcionalidades avançadas do editor.

## Gates finais

`run_remaining_gates.py` executa 23 verificações registradas: unit test nativo verde/vermelho/verde com mutação SQL; contrato de tabela com tipo/nome incompatíveis; consultas semiaditivas em múltiplos grãos, null e mutação da configuração; driver de docs verificado, rejeição de corrupção e geração isolada do cache global/rede. Os resultados estão em `evidence/remaining-gates-results.json`.

O saldo total correto é 390; remover non_additive_dimension produz 1.380 e é detectado pelo oráculo. Em janeiro, última data comum retorna 110 e última observação por conta retorna 330; conta B na data comum é null. Essas métricas têm nomes distintos e não substituem a regra de fechamento oficial/coverage do projeto real.

Para gerar docs, compile estritamente e execute `.venv-mf/bin/python pinned_docs.py`. `--prepare` aproveita cache já baixado e verificado; `--bootstrap` permite preparação online explicitamente. Nunca envolver o wrapper em outro sandbox-exec: ele aplica o bloqueio de rede e cache ao processo dbt internamente. Ver [relatório final](../../specs/compatibility-final-gates.md).
