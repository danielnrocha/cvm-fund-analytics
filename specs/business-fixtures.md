# Fixtures e testes de negócio — 28/10/2026

Escopo autorizado: validar contratos antes da pipeline completa. Foi criado um [laboratório executável](../tests/business/README.md) com unittest, fixture sintética e DuckDB do ambiente fixado. O laboratório não constrói tabelas persistentes, modelos dbt, Raw Vault ou gateway.

| Risco | Evidência de comportamento |
|---|---|
| Duplicação física | Duas ocorrências idênticas viram uma observação lógica, mantendo ambas as proveniências |
| Conflito no mesmo grão/captura | Mesmo PL, fluxo diferente: bloqueio; não escolher última linha arbitrariamente |
| Perda de versão | A→B→A em capturas distintas preserva as três versões; repetição da mesma ocorrência não adiciona versão |
| Colisão de identidade | Fundo/classe separados; subclasse vinculada ao pai; CNPJ mascarado normalizado sem descartar letras inválidas |
| Cadastro desconhecido/ambíguo | Bloqueio explícito, sem escolher uma correspondência por ordem |
| Fanout ou perda no join | Uma correspondência exigida por fato; quantidade e PL conservados |
| Missing disfarçado de zero | Fluxo zero observado permanece distinto de par classe/data ausente |
| Corte sem dados | PL null no corte contratado; não recuar automaticamente |
| Denominador incorreto | Universo/calendário fixos; população vazia não produz resultado certificado zero; fato duplicado bloqueia |

Os testes usam expectativas literais calculadas à mão. A soma temporal 410 aparece exclusivamente como invariante de conservação, não como métrica de patrimônio. O fechamento contratado é 110 e cobertura 1/2; fluxo reportado é 30 e cobertura 3/4.

## Evidências TDD e mutação

Primeiro foram escritos fixture, testes e stubs sem comportamento. [Vermelho](../tests/business/evidence/01-red.log): 12 testes, 14 falhas de assertions contando subtests. Depois foi adicionada a implementação mínima do probe; [primeiro verde](../tests/business/evidence/02-green.log): 12 testes passaram.

[Seis mutações](../tests/business/evidence/mutations.json) exercitam defeitos: inflar duplicatas, remover captura da chave, colapsar subclasses, escolher correspondência cadastral arbitrária, recuar corte e converter missing para zero. Todas devem produzir falhas de assertions em uma cópia descartável. A suíte não pretende medir cobertura por percentual de linhas.

## Limites de prova

- Fixture reduzida e sintética; não substitui fixtures com todos os campos do CSV real.
- Aditividade universal, histórico cadastral e retornos continuam não homologados.
- `resolve` recebe namespace interno e tabela de mapeamento; não implementa a política completa de seleção da coorte.
- Deduplicação compara os campos de payload presentes no laboratório. Produção deve comparar todos os campos de negócio relevantes e manter o original.
- Teste A→B→A é de identidade/versionamento em memória; persistência append-only, idempotência operacional, full rebuild/incremental e promoção continuam pendentes.
- Testes de modelos dbt nativos e consultas MetricFlow desses cenários serão executados quando os modelos existirem. Gates técnicos anteriores permanecem distintos.

Revisão adversarial independente e resultados finais estão em [reviews/business-fixtures-review.md](../reviews/business-fixtures-review.md).

## Correção motivada pela revisão

O revisor identificou overflow no fluxo derivado armazenado com a precisão da origem. Um teste de limite adicional falhou por assertion antes da correção ([vermelho](../tests/business/evidence/03-review-red.log)); o probe passou a usar DECIMAL(38,2) para fluxo. A suíte final tem 13 testes. Também foi corrigida a descrição de status no contrato de dados. O parecer independente registra a verificação da correção separadamente.
