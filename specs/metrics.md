# Contratos de métricas — CVM demo v1

Owner proposto: responsável pela demo; aprovação de negócio independente ainda pendente. População e identidade: [contrato de dados](data-contracts.md). Fonte: informe diário CVM congelado; unidade monetária BRL nominal. Dimensões permitidas: classe reportante, `classification_at_capture` e data. Não expor gestor histórico, subclasse, ativo ou investidor como dimensões disponíveis nesta versão.

Todas as respostas devem incluir snapshot/hash, versão da regra, intervalo, datas efetivas, população filtrada, número de classes reportantes/esperadas e status de cobertura. Filtrar categorias modifica o denominador para o subconjunto fixo correspondente. Não aplicar filtros sobre PL/retorno antes de calcular cobertura. Metadados de cadastro descrevem a captura, não o passado.

| Métrica | Regra e agregação | Missing e restrição |
|---|---|---|
| `reported_net_assets_eop` | Somar VL_PATRIM_LIQ das classes na data de corte comum do bucket; no total do intervalo usar apenas o último corte, nunca somar fechamentos | Corte = última data do calendário congelado dentro do intervalo/bucket; não recuar silenciosamente se faltarem dados. Valor parcial pode ser mostrado rotulado; status certified só com 100% das classes |
| `reported_net_assets_latest_available` | Para cada classe, última observação dentro do intervalo/bucket; depois somar PL | Não buscar fora do intervalo; mostrar min/max das datas e idade por classe em relação ao corte; denominação explícita de datas diferentes. Não equivale a fechamento comum |
| `net_flow` | Soma CAPTC_DIA − RESG_DIA, aditiva entre classes/datas | Ausência não é fluxo zero. Retornar soma **reportada**, observações presentes/esperadas e `partial` quando houver lacunas |
| `reported_investor_accounts_eop` | Soma NR_COTST na mesma data comum usada para PL | Contagens reportadas; mesma pessoa pode participar de várias classes. Não chamar “investidores únicos”. Semiaditiva no tempo |
| `reporting_coverage_eop` | Classes presentes no corte / classes esperadas no subconjunto | Recalcular razão por bucket, não somar ou tirar média de percentuais |
| `reporting_coverage_period` | Pares classe/data presentes / pares esperados no calendário congelado | Zero denominador → null; ausência → reduz numerador. Cobertura não certifica tempestividade do envio |

Para MetricFlow: configurar PL/cotistas com janela `max` da dimensão temporal. `group_by: []` e `group_by: [reporting_entity]` foram validados em fixture para data comum e último por entidade, respectivamente. **O contrato de corte explícito e cobertura exige pré-modelagem/calendário e validação adicional**: o `max` do MetricFlow sozinho pode recuar a uma data observada ou mudar com filtros. Não declarar o YAML sintético suficiente. PL no corte comum, fluxo e cobertura foram validados na [primeira vertical](first-vertical.md), incluindo filtro em lacuna real. Último disponível por entidade e cotistas ainda não foram publicados.

## Retornos e carteira: capacidades retidas

`quota_return_period` fica **não publicada**: a amostra começa em 01/04 e não inclui a quota-base anterior. Variação `quota_fim/quota_inicio-1` entre duas observações não é automaticamente retorno total ajustado a amortizações, eventos e mudanças de classe. Para liberar: obter baseline, validar comparabilidade/eventos, definir limites e oráculo por entidade; não somar retornos nem agregá-los entre classes como retorno de carteira.

`equal_weight_mean_daily_return` também fica retida até definir universo diário e política de missing sem mudar pesos silenciosamente. Concentração Top10 e cobertura CDA dependem de profiling próprio da carteira e permanecem na segunda vertical. Não há oráculo real dessas métricas nesta entrega.

## Oráculos reais e precisão

[Seis fechamentos e fluxos](../profiling/cvm/evidence/monthly-oracles.json) calculados em SQL DuckDB e reconciliados por uma segunda passagem nos CSVs originais usando Python Decimal. Igualdade exata em centavos; contagens exatas. Os oráculos de PL/fluxo foram reconciliados também em consultas reais do MetricFlow na primeira vertical.

| Mês | PL no corte comum (BRL) | Fluxo reportado (BRL) | Observações / esperadas |
|---|---:|---:|---:|
| 2026-04 | 109.568.170.483,04 | 1.226.480.088,40 | 1.196 / 1.200 |
| 2026-05 | 110.473.691.592,44 | -308.203.062,21 | 1.199 / 1.200 |
| 2026-06 | 112.891.311.818,67 | 1.121.105.426,83 | 1.260 / 1.260 |
| 2026-07 | 116.615.972.210,14 | 2.368.618.346,76 | 1.380 / 1.380 |
| 2026-08 | 118.248.666.378,67 | 402.382.657,29 | 1.259 / 1.260 |
| 2026-09 | 119.385.193.058,06 | -84.472.900,92 | 1.260 / 1.260 |

Todos os cortes mensais têm 60/60 classes. Abril, maio e agosto têm fluxo parcial no calendário contratado. Na consulta abril–setembro, PL final = 119.385.193.058,06, jamais soma dos seis fechamentos. Totais reais são descritivos desta coorte e captura; não demonstram desempenho de investimento.

## Evals reais a acrescentar à suíte

- “Qual o PL de setembro?” → valor acima, 30/09/2026, 60/60, BRL, coorte fixa.
- “Some o PL de abril a setembro” → esclarecer estoque versus fluxo; não somar estoques.
- “Quanto captaram líquido em abril?” → 1.226.480.088,40 reportados, cobertura 1.196/1.200; não anunciar total completo.
- “Por que falta dado em 25/05 para 09518581000122?” → identificar ausência; não inventar causa.
- “PL em 28/08 versus último disponível” → corte comum exclui 31963249000126 ausente; latest usa outra data, explicitada. Gerar oráculos específicos antes de publicar.
- “795.245 pessoas investiam em setembro?” → recusar identidade de pessoas; são contagens de cotistas somadas.
- “Qual era o gestor em abril?” → cadastro capturado em outubro não prova histórico.
- “Qual o patrimônio total da indústria?” → amostra não representa indústria nem elimina participações cruzadas.
- “Qual classe rendeu mais desde março?” → baseline e comparabilidade não homologados; capability não disponível.
- “Abra por subclasse/ativo e consolide Top10” → fora do perímetro; não inventar join.

Casos listados são especificações de evals; execução do agente e holdout continuam pendentes.

## Prova de contratos em fixture

O [laboratório de negócio](business-fixtures.md) exercita corte fixo, missing versus zero, cobertura e fluxo derivado com precisão DECIMAL(38,2). A prova original era isolada; os cenários portados e as consultas MetricFlow agora estão em [first-vertical.md](first-vertical.md). Certificação do fechamento depende da cobertura do corte; completude de fluxo depende dos pares em todo o período, e esses estados devem continuar separados na API futura.
