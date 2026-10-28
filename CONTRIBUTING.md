# Contributing

Use `make setup`, then `make test`. For model or metric changes run `make build` and `make metrics`. No local Docker is required. The complete Linux acceptance runs in GitHub Actions.

Describe the business behavior, input grain and metric impact in the PR. Add a failing fixture before changing logic, then run the relevant checks. Keep frozen oracles unchanged unless the source or business contract change has been explicitly reviewed.

Do not update the baseline hash to make a failing PR green. A baseline change requires a separately reviewed release, new tag/asset and a lock update. Release assets, raw archives, virtual environments, generated databases and credentials do not belong in Git.

Protected `main` requires a PR, an up-to-date `validate` check from GitHub Actions, resolved review conversations and linear history, including administrator changes. Use squash merge after the current revision passes. Force-pushes and deletion are disabled. Second-person approval is optional for this sole-maintainer portfolio; see [policy and acceptance evidence](specs/main-protection.md).
