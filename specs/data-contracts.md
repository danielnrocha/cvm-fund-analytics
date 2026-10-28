# Contratos de dados CVM — v1

Decisão de 28/10/2026. Contratos para implementação futura; profiling executado em [relatório](cvm-profiling.md). Fonte canônica: dicionários oficiais preservados por hash no [manifest](../profiling/cvm/evidence/sources.json). Os arquivos CSV oficiais são Latin-1, delimitados por `;`; o envelope JSON é uma representação derivada nossa, não um formato oferecido por esse recurso CVM.

## Identidade e temporalidade

| Objeto | Grão contratado | Restrição |
|---|---|---|
| Captura | URL × SHA-256 do arquivo | `captured_at` UTC, competência, licença, tamanho, versão do parser; não sobrescrever bytes |
| Observação de origem | SHA-256 × membro ZIP × linha física | Preservar cada ocorrência, inclusive duplicatas; cabeçalho não é observação |
| Fundo cadastral | `CVM:FUND:ID_Registro_Fundo` | CNPJ é atributo/string; IDs repetidos existem na origem, não assumir dimensão pronta |
| Classe cadastral | `CVM:CLASS:ID_Registro_Classe` | Relação com `ID_Registro_Fundo`; resolução de conflitos obrigatória |
| Subclasse cadastral | classe pai × `ID_Subclasse` | Embora globalmente único nesta captura, manter escopo do pai; string opaca, sem conversão numérica |
| Informe bruto | tipo original × CNPJ normalizado × ID_SUBCLASSE nullable × DT_COMPTC × observação | Não apagar tipo nem substituir ausência por uma subclasse inventada |
| Fato da demo | `CVM:CLASS:ID_Registro_Classe` × DT_COMPTC × versão selecionada | Apenas as 60 classes congeladas; ID_SUBCLASSE ausente; uma observação lógica por classe/dia |

Cadastro atual não é cadastro historicamente válido. A classificação usada para estratificar é `classification_at_capture`, nunca “classificação naquela data”. Preservar o tempo de observação e, futuramente, mudanças observadas; não retroagir uma SCD2 ao início do informe. IDs e relações desta captura não provam continuidade em incorporações, adaptações ou cisões.

No Raw Vault futuro, duplicatas físicas são evidência; o satélite distingue versão de negócio de repetição do mesmo payload. Duplicata idêntica pode gerar uma única observação lógica com todas as proveniências. Dois payloads distintos na mesma chave/captura bloqueiam publicação até resolução explícita; ordem da linha não determina “última versão”. No recorte escolhido, não há essas duplicatas.

## Campos do informe

| Campo de origem | Tipo contratado | Política |
|---|---|---|
| TP_FUNDO_CLASSE | VARCHAR | Obrigatório, conservar valor original; demo aceita `CLASSES - FIF` |
| CNPJ_FUNDO_CLASSE | VARCHAR | Guardar original; normalizar máscara para 14 dígitos neste snapshot; nunca BIGINT. Futuro formato alfanumérico exige nova versão do contrato |
| ID_SUBCLASSE | VARCHAR nullable | Até 15 caracteres conforme dicionário; ausência não é zero |
| DT_COMPTC | DATE | Obrigatório, ISO; deve pertencer à competência do arquivo |
| VL_TOTAL, VL_PATRIM_LIQ, CAPTC_DIA, RESG_DIA | DECIMAL(17,2) | Fonte sem arredondamento silencioso; somas DECIMAL(38,2) |
| VL_QUOTA | DECIMAL(27,12) | Não usar FLOAT para ingestão/oráculo |
| NR_COTST | BIGINT | Integral, >= 0; não significa pessoas únicas |

Nulls e casts inválidos não apareceram nesses seis campos numéricos nesta captura. Na implementação: campo obrigatório inválido → quarentena e reconciliação por arquivo, nunca zero. Antes de cast, validar escala e precisão lexical para impedir arredondamento silencioso. PL e quota negativos existem no universo real: emitir flag de domínio, não impor `PL >= 0` global nem apagar a evidência. Retornos exigem quotas estritamente positivas.

Schema ausente ou coluna obrigatória renomeada bloqueia o batch. Coluna nova é preservada no raw e exige revisão antes de consumo tipado. `lidos = aceitos + rejeitados` em cada arquivo; contagens de duplicatas lógicas são separadas das contagens físicas. Falhas da coorte impedem promover um novo snapshot; manter publicação anterior.

## Elegibilidade congelada

Abril–setembro/2026, 60 classes: 20 de Renda Fixa, 20 de Multimercado e 20 de Ações. [Lista](../profiling/cvm/evidence/cohort.csv) é o contrato da população. Algoritmo em `profiling/cvm/cohort.py`: CNPJ e ID de classe sem ambiguidades; ID de fundo pai com exatamente uma linha; exatamente uma classe por fundo; nenhuma subclasse no cadastro ou nos informes; um único tipo `CLASSES - FIF`; dia único por CNPJ; presença nos seis meses. Ordenar SHA-256 do CNPJ, desempatar CNPJ, selecionar 20 por classificação.

Não filtrar rentabilidade, tamanho do PL, situação “ativa” ou desempenho. Exigir seis meses introduz viés de continuidade/disponibilidade; esta é amostra didática estratificada, não representativa. Cada nova captura deve preservar a lista e avaliar divergências, nunca resselecionar silenciosamente as 60.

A exclusão da hierarquia sobreposta elimina dupla contagem estrutural fundo/classe/subclasse. **Não elimina participações entre fundos**: PL agregado é soma dos patrimônios reportados da coorte, não riqueza econômica consolidada nem ativos da indústria.

## Calendário, cobertura e joins

Congelar [126 datas observadas na coorte](../profiling/cvm/evidence/calendar.json), sem anunciar calendário oficial de negociação. Há seis pares classe/data ausentes em 7.560 esperados; preservar como missing. O universo completo tem cinco datas adicionais sem observação na coorte: usar esse universo como calendário produziria 306 ausências artificiais/observadas misturadas. Um calendário regulatório externo continua fora do contrato v1.

Join do fato com dimensão resolvida deve conservar contagem e soma de PL; máximo uma correspondência. CNPJ que aparece em fundo e classe não autoriza escolher nível por precedência: tipo da origem, cadastro e elegibilidade devem concordar. Unknown e ambiguidade são estados explícitos fora da população certificada. Não fazer join direto com cadastro bruto, subclasses ou carteira mensal.

## Testes de aceite para a pipeline futura

1. Chaves e proveniência obrigatórias; unicidade do fato resolvido e integridade das relações elegíveis.
2. Reconciliar 7.554 linhas e seis fechamentos de 60 classes com o snapshot congelado.
3. Reproduzir os seis missing reais; não preenchê-los com zero ou forward-fill.
4. Duas duplicatas idênticas do conjunto diagnóstico não duplicam métricas; conflito sintético distinto bloqueia publicação.
5. Cadastro com múltiplos registros não multiplica fato; tipo desconhecido vai para resolução explícita.
6. Full rebuild e incremental equivalentes; replay/A→B→A, sem inventar histórico de reapresentações reais.

O profiling, os oráculos e o laboratório sintético de [fixtures de negócio](business-fixtures.md) foram executados. Duplicatas, lacunas, identidade e fanout têm testes de contrato isolados; a [primeira vertical](first-vertical.md) acrescenta modelos dbt, testes nativos e integração de capturas. Parsing completo, hubs/links e integração da pipeline inteira continuam pendentes. Fluxos derivados e agregações usam DECIMAL(38,2): a diferença de dois DECIMAL(17,2) assinados pode exceder a precisão da origem.

## Atualização: ingestão por sources

A [ingestão CVM](ingestion.md) substitui os seeds descritos anteriormente: ZIPs preservados por SHA-256, envelopes JSON, sources físicos, quarentena e reconciliação por arquivo. População/calendário permanecem contratos congelados. Oráculos e histórico mínimo foram preservados; consulte o documento para escopo e evidências atuais.

## Atualização: publicação de snapshots — 28/10/2026

A [publicação atômica local](snapshot-publication.md) implementa bundles verificados, ponteiros independentes dev/UAT, rollback e leitores read-only fixados na release. Substitui referências anteriores a promoção local pendente; CI Linux e pipeline completa continuam fora deste aceite. PL e fluxo permanecem reconciliados com os mesmos seis oráculos reais.
