# Profiling real CVM — 28/10/2026

Escopo concluído: seis arquivos mensais de informe diário (abril–setembro/2026), cadastro fundo/classe/subclasse e dicionários oficiais. 3.227.984 linhas diárias analisadas em DuckDB local. Sem implementação de ingestão operacional, Vault, marts ou gateway de IA.

Fontes primárias: [catálogo do informe diário](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario), [catálogo cadastral](https://dados.cvm.gov.br/dataset/fi-cad), [dicionário diário](https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/META/meta_inf_diario_fi.txt), [dicionários cadastrais](https://dados.cvm.gov.br/dados/FI/CAD/META/meta_registro_fundo_classe.zip). Catálogos declaram ODbL. Cadastro é posição atual; informes podem receber reapresentações. Conservar atribuição à CVM, URLs e licença. Dados brutos permanecem locais/ignorados; antes de redistribuir banco derivado, documentar atribuição e obrigações ODbL aplicáveis.

## Evidências que mudam o design

| Achado observado | Implicação |
|---|---|
| 90.876 linhas cadastrais de fundo, 89.721 IDs e 81.949 CNPJs distintos | Nem ID nem CNPJ bruto garantem uma linha de dimensão; não usar `unique` na origem sem resolução |
| 37.010 linhas de classe, 37.005 IDs e 36.997 CNPJs distintos | Join direto também pode multiplicar fatos nesse nível |
| 11.518 subclasses, IDs únicos nesta captura | Modelar chave com classe pai mesmo assim; uma captura não garante unicidade universal |
| Nenhuma relação cadastral classe→fundo ou subclasse→classe órfã | Integridade de existência observada; não prova unicidade nem vigência histórica |
| Dois grupos de chave diária repetida | CNPJ 49.963.346/0001-84 em 07 e 08/07, duas linhas idênticas por dia; preservação física e deduplicação lógica são diferentes |
| 28.187 pares CNPJ/data com mais de uma subclasse | CNPJ × dia não é grão universal; PL difere entre subclasses em exemplos reais |
| Zero pares com subclasse presente e ausente simultaneamente | Não foi observada sobreposição explícita desses níveis no mesmo dia; não basta para provar aditividade econômica universal |
| 3.445 informes com subclasse sem match hierárquico no cadastro atual | Não fabricar relação histórica; pode refletir diferenças temporais, causa não diagnosticada |
| 87.649 linhas `CLASSES - FIF` sem CNPJ de classe no cadastro atual | Cadastro de outubro não resolve automaticamente todo o período anterior |
| 3.975 PLs negativos e 3.990 quotas negativas no universo | Regra global `>= 0` rejeitaria dados reais; separar validade sintática de elegibilidade da métrica |

O join exploratório simultâneo por CNPJ com classe e fundo expande as 3.225.291 linhas `CLASSES - FIF` para 3.513.563. A seção `joins` do JSON registra **contagens pós-join deliberadamente inseguro**, não tamanho da fonte. `daily_membership` usa EXISTS e não sofre fanout. Linhas múltiplas do cadastro não foram classificadas automaticamente como erro: podem conter relações/atributos distintos; a coorte as exclui.

Os seis campos numéricos do informe não têm nulls nem falha de conversão para os tipos do dicionário no snapshot. Isso não prova validade econômica nem substitui testes lexicais contra arredondamento na pipeline futura.

## Recorte escolhido

**60 classes, abril–setembro/2026, 7.554 observações, 126 datas observadas.** 20 classes por classificação atual: Ações, Multimercado e Renda Fixa. Seleção determinística SHA-256 do CNPJ sobre 3.861, 12.472 e 6.634 elegíveis, respectivamente. Sem escolha por desempenho ou PL. Regras e limites em [data-contracts.md](data-contracts.md); lista e código auditáveis abaixo.

Cada classe tem um único pai resolvido, o pai só tem uma classe e não há subclasses no cadastro/informe selecionados. Há seis lacunas reais em 7.560 pares classe/data esperados; todos os seis cortes mensais têm 60 observações. Não há PL negativo nem quota não positiva na coorte. Mantivemos as lacunas: elas permitem mostrar que fluxo parcial e fechamento completo podem coexistir.

O calendário observado do universo completo tem cinco datas a mais do que o da coorte; usar todo o universo como calendário confundiria 300 pares nessas datas com seis lacunas internas. O calendário congelado é uma convenção didática declarada, não calendário regulatório validado.

Tradeoff: a coorte simplifica a hierarquia para métricas confiáveis e introduz viés de continuidade ao exigir presença nos seis meses. Complexidades excluídas permanecem no conjunto diagnóstico, não são somadas às métricas. Não é amostra representativa nem consolidação de participações entre fundos.

## Artefatos e reprodução

- [Manifest de fontes, tamanhos e SHA-256](../profiling/cvm/evidence/sources.json).
- [Perfil completo](../profiling/cvm/evidence/profile.json), [perfil da coorte](../profiling/cvm/evidence/cohort-profile.json), [casos reais](../profiling/cvm/evidence/edge-cases.json).
- [60 classes](../profiling/cvm/evidence/cohort.csv), [calendário](../profiling/cvm/evidence/calendar.json), [oráculos mensais](../profiling/cvm/evidence/monthly-oracles.json).
- [Instruções de reprodução](../profiling/cvm/README.md).

Doze [assertions do snapshot](../profiling/cvm/evidence/validation.json) passaram, incluindo hashes, grão, formato de CNPJ, competência dos arquivos e cobertura.

Conferência dos seis meses: DuckDB DECIMAL e passagem independente nos CSV originais em Python Decimal reconciliaram exatamente PL, fluxo, contagem de cotistas e observações. Independência de cálculo não equivale a revisão independente por outra pessoa/agente. A coorte é escolhida pelo SQL; o oráculo Python usa a mesma lista fixa.

## Limites e próximo gate

G1 fechado para **essa população limitada**: fontes, grão, recorte, contratos e oráculos definidos. Não homologado: aditividade universal de subclasses, histórico cadastral de abril, reapresentações ao longo do tempo, retornos ajustados, CDA e métricas reais no MetricFlow. Um único download não recupera versões anteriores.

Próximo passo previsto: fixtures de negócio e testes vermelhos de parsing, identidade, duplicatas, missing e fanout. Depois, implementação de uma vertical mínima até PL/fluxo. A pipeline completa continua não implementada; retorno e carteira são capacidades bloqueadas até seus gates próprios.
