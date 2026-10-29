# Repository refactor implementation plan

Approved design: repository-review.md. Execution uses TDD and independent adversarial review; no Docker locally and no analytics agent.

- [x] Add failing behavioral tests for semantic mutation discovery across old/new layouts, metric ordering, duplicate definitions and repeated mutations; implement fail-closed helpers and use them in rehearsal and negative gates.
- [x] Move SQL into the approved responsibility folders without renaming nodes; colocate YAML, preserve parsed definitions, update active path consumers and documentation.
- [x] Configure native dbt lint/format, editor defaults and remote style gates. Review SQL changes, retain tuple-distinct semantics and incremental replay behavior.
- [x] Validate Python suite, native tests/build in an isolated project, exact MetricFlow totals/monthly/gaps, red/green exercises and required column-lineage edges.
- [x] Independently review changes, resolve material findings and record evidence/remaining limitations in the spec and delivery plan.

Primary files: transform/models/**, transform/.sqlfluff, demo/mutations.py, demo/rehearse.sh, scripts/check_semantic_mutation.py, tests/ci/check_semantic_gate.py, tests/demo/test_mutations.py, .vscode/**, Makefile, .github/workflows/linux-ci.yml. Preserve historical evidence and old baseline assets. No baseline rotation.

Acceptance: [independent review and results](../reviews/repository-refactor-review.md). Remote Linux execution is not claimed; changes remain local.
