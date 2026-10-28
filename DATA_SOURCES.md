# Data sources and attribution

Source: Comissão de Valores Mobiliários (CVM), Brazil — [daily investment fund reports](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario) and fund/class registration datasets. This project is independent and is not endorsed by CVM, Base dos Dados or dbt Labs.

The exact public URLs, observation timestamps, byte lengths and SHA-256 digests are in [sources.json](profiling/cvm/evidence/sources.json). The [profiling report](specs/cvm-profiling.md) records source/license findings and the cohort selection. CVM data attribution and applicable Open Database License (ODbL) terms remain separate from the project's code. Preserve attribution and applicable database obligations when redistributing the baseline database; dependency licenses also remain their own.

Only corporate fund/class identifiers and public aggregate reports are used; the demo does not contain investor-level records. The cohort is deliberately limited, and overlapping fund exposures are not consolidated.

Raw ZIPs, databases, virtual environments and generated build state are excluded from Git. The approved baseline database is distributed separately as a pinned Release asset. Historical source URLs are mutable: the downloader rejects changed bytes. Keeping a baseline does not make the upstream raw archives immutable or guarantee their future availability. A future source update requires reviewed new captures, profiling and oracle acceptance, not a hash bypass.

No repository-wide code license has been selected yet. Public visibility does not itself grant a software license; select a license before advertising this project as reusable open source.
