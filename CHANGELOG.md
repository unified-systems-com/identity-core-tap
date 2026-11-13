# Changelog

## [0.1.7](https://github.com/unified-systems-com/identity-core-tap/compare/v0.1.6...v0.1.7) (2026-11-13)


### Features

* declare Dimension nodes for this plugin's dimension keys ([#41](https://github.com/unified-systems-com/identity-core-tap/issues/41)) ([2210ec8](https://github.com/unified-systems-com/identity-core-tap/commit/2210ec80043efcd099a7e179f83ef9b6fb4c73e7))
* email address, mailbox and phone number types, and the edges that tie records to them ([5da1d87](https://github.com/unified-systems-com/identity-core-tap/commit/5da1d8792977d59ac2af5565d68149006d05d23e))
* email address, mailbox and phone number types, and the edges that tie records to them ([4fb9c4b](https://github.com/unified-systems-com/identity-core-tap/commit/4fb9c4b36e9f310bd25912e47ab6d46ac70d32b6))


### Bug Fixes

* a malformed local part or domain label is not an email address ([b11fc24](https://github.com/unified-systems-com/identity-core-tap/commit/b11fc24d2852b9d329e37ec5191b8be9629333b1))
* the canonical email form is stable, and an unquoted local part holds only what RFC 5322 allows ([d6207cc](https://github.com/unified-systems-com/identity-core-tap/commit/d6207cc4db4b3bbea483744b8512b02eb13e2806))
* the migration depends on the plugin's minimum tap, and the spec owns the case-folding choice ([0eed42f](https://github.com/unified-systems-com/identity-core-tap/commit/0eed42f1cb5fce30992e49f1ecb0e87480e6e476))

## [0.1.6](https://github.com/unified-systems-com/identity-core-tap/compare/v0.1.5...v0.1.6) (2026-10-21)


### Features

* **team:** ANSWERS_FOR_DIMENSION, a team to a dimension node ([bcf5215](https://github.com/unified-systems-com/identity-core-tap/commit/bcf521537783f9fabd7c659b78485729f6ad7a59))
* **team:** ANSWERS_FOR_DIMENSION, a team to a dimension node [via Claude Code] ([df6a9f9](https://github.com/unified-systems-com/identity-core-tap/commit/df6a9f911a454d0647361d07b3e5ef6003c162ea))


### Documentation

* **spec:** drop the unverifiable approval attribution [via Claude Code] ([f38c6fd](https://github.com/unified-systems-com/identity-core-tap/commit/f38c6fd49dfe7bf25d7027d9ffb29610543573f2))
* **spec:** drop the unverifiable approval attribution from responsible-6 ([3ce6e21](https://github.com/unified-systems-com/identity-core-tap/commit/3ce6e212b57c5822d2e2a8e8db0c1e235a4b20a7))

## [0.1.5](https://github.com/unified-systems-com/identity-core-tap/compare/v0.1.4...v0.1.5) (2026-10-21)


### Features

* **team:** identity_core team model, BELONGS_TO_TEAM and LEADS_TEAM edges [via Claude Code] ([a1ac92f](https://github.com/unified-systems-com/identity-core-tap/commit/a1ac92f11c2c37c94bcc6b6956d40e4d011b9986))
* **team:** the team model, BELONGS_TO_TEAM and LEADS_TEAM, and the team.responsible convention ([1b70a24](https://github.com/unified-systems-com/identity-core-tap/commit/1b70a241a368d9dd846c662815cb0e2a8b93372d))


### Documentation

* **spec:** identity_core team — the model, BELONGS_TO_TEAM and LEADS_TEAM, and the team.responsible stamp ([5d2b24f](https://github.com/unified-systems-com/identity-core-tap/commit/5d2b24f75025f8c65261608d1656c71971433a35))
