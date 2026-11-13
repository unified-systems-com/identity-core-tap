# Identity Core Plugin Specification

## Plugin Identity

- **Slug:** `identity_core`
- **Kind:** substrate library plugin — vocabulary + mechanism, **no collector in v0**.
- **Public surface:**
  - **Models** (see `req-identity-core-model`, `req-identity-core-organization`, `req-identity-core-human`, `req-identity-core-team`): `oidc_issuer`, `organization`, `human`, `team`.
  - **Helpers** (see `req-identity-core-issuer-id`, `req-identity-core-canonical-url`,
    `req-identity-core-envelope`):
    - `identity_core.issuer.canonical_issuer_url(raw: str) -> str` — the one canonical
      normalization every observer runs before keying an issuer.
    - `identity_core.issuer.oidc_issuer_id(raw: str) -> UUID` — the deterministic entity
      id, derived from the canonical form. The **only** way to compute an issuer id.
    - `identity_core.issuer.oidc_issuer_node_envelope(raw: str, *, dimensions=None)
      -> <node envelope>` — mints a GRIFT node fragment a consumer merges into its own
      batch. (The `display_name` param from the original design is dropped in v0: the
      entity spine projects `get_name()`=issuer_url on save, so a divergent name would
      not survive — the node name is always the issuer_url.)
  - **Edge types:** one — `TRUSTS_ISSUER__identity_core` (generic, **wildcard source**,
    target `identity_core__oidc_issuer`). Trusting an OIDC issuer is a cross-cloud
    federation relationship (AWS/GCP/Azure/k8s/Vault all do it), so the substrate owns
    the generic vocabulary; the wildcard source keeps deps downward-only. Owning the
    type asserts no trust (existence != trust) — instances exist only when an emitter
    creates the edge. The other issuer-touching edges (`ENABLED_ON`, `IDENTITY_VOUCHED_BY`)
    are domain-specific and stay with the plugin that asserts them
    (`req-identity-core-edge-retargets`).
  - **Team edges** (added 2026-10-20, see `req-identity-core-team-edges`): `BELONGS_TO_TEAM__identity_core` (a human or a team belongs to a team) and `LEADS_TEAM__identity_core` (a human leads a team). `ANSWERS_FOR_DIMENSION__identity_core` (a team to a dimension node, added 2026-10-21, `req-identity-core-responsible-6`) records which dimension key a team's id is stamped under.
  - **Default dimensions** (see `req-identity-core-dimensions`): `identity.protocol: oidc`. The ownership stamp `team.responsible` (`req-identity-core-responsible`) is a convention for other plugins' entities, not a default.

## Philosophy

Identity is cross-cutting substrate, not domain payload. An OIDC issuer is a
**convergence node**: github references its Actions issuer, AWS IAM federates trust
into an issuer, Sigstore binds signing certs to identities vouched by an issuer. In
v0 it landed inside `github_core` (`github_core__oidc_issuer`) purely because github
was the first plugin to need it — and the coupling shows: `samsite`'s compliance
collector reaches *into github's collector code*
(`from tap_plugin.github_core.collectors.github_collector.identity import
oidc_issuer_id`) just to compute the issuer's id. That is a domain plugin owning a
primitive three other plugins depend on. The fix is the substrate-core extraction
doctrine: hoist the issuer to a neutral plugin everyone depends on **downward**.

Three principles shape the design:

**Mechanism, not catalog.** identity_core ships the *general* capability to mint an
issuer node from a URL — not a seeded list of well-known issuers. A seed list is a
special-case that only defers the real question (*how does a non-well-known issuer
get in?*) to the worst possible moment: when it is blocking someone. We solve the
general case once, now. Any observer that sees an issuer URL synthesizes the node
through the one helper; observers converge on the same node by deterministic id.

**Existence is not trust.** An `oidc_issuer` node records only that *an issuer
identity was referenced*. It asserts nothing about whether the issuer exists in the
world, is reachable, or is trusted. Trust is a **separate, explicit edge** a specific
principal asserts (`aws_iam_oidc_provider —TRUSTS_ISSUER→`, `rekor_log_entry
—IDENTITY_VOUCHED_BY→`). The substrate never takes a position on trust; it only gives
identities a place to converge. This is the security posture applied: no trust is
smuggled in through the mere presence of a node.

**Convergence is owned here.** github keys the issuer by its full OIDC `iss`
(`https://token.actions.githubusercontent.com`); AWS IAM stores the scheme-less host
(`token.actions.githubusercontent.com`). For independent observers to land on **one**
node, the canonical form must be defined in exactly one place. identity_core owns that
normalization, so convergence is guaranteed rather than coincidental.

## Roadmap Alignment

Realizes the **substrate-core plugin extraction** doctrine (generic cross-cutting
vocabulary lives in neutral `*_core` substrate plugins that domain plugins depend on
downward). Sibling of the `compliance_core` extraction. Advances the cross-plugin
decoupling line: removes the `samsite → github_core` code import and makes
`github_core` independent of the identity primitive. Pre-eviction work — the
`entity_type` rename is namespace churn that must land before plugins are frozen at
released tags (`req-identity-core-migration`).

AI-integration posture: the issuer is machine-legible identity vocabulary with a
described, queryable node type; the "who does this identity converge" question becomes
a one-hop graph traversal rather than code-reading.

## Prior Art

- **OIDC issuer identifier** (OpenID Connect Core / RFC 8414): the `iss` is a
  case-sensitive URL, `https` scheme, no query or fragment, optional path — the natural
  key this node is built on.
- **Sigstore/Fulcio:** the signing certificate carries the issuer as a claim; Sigstore
  verification policy matches on it (samsite's `artifact_manifest` pins
  `oidc_issuer: https://token.actions.githubusercontent.com`).
- **AWS IAM OIDC provider:** stored scheme-less; the reason canonical normalization
  must span scheme'd and scheme-less forms.

## Goals

|   |   |   |
| :---: | --- | --- |
| 1. | Identity Substrate | A neutral home for cross-cutting identity vocabulary; `oidc_issuer` is the v0 tenant. |
| 2. | Library Plugin | No collector in v0. The public surface is the model + Python helpers consumer collectors call. |
| 3. | General-Case Synthesis | Any observer mints an issuer from a URL via one helper; no seeded well-known catalog, no assumption an issuer exists. |
| 4. | Existence ≠ Trust | The node records reference/existence only; trust lives on explicit edges owned by the asserting plugin. |
| 5. | Convergence Owned Here | One canonical URL normalization + one id derivation, so independent observers land on one node. |
| 6. | Downward-Only Deps | github / aws_core / sigstore_core / samsite depend on identity_core; identity_core depends on nothing above core. |
| 7. | Minimal Node | URL identity + a little observed metadata; no issuer-metadata fetch, no liveness, no policy. |

## Requirements

| RID | Name | Status | Notes |
| --- | --- | :---: | --- |
| req-identity-core-scope | [Plugin Scope](#plugin-scope) | Implemented | Substrate library; `oidc_issuer` model + issuer helpers; no collector, no owned edges. |
| req-identity-core-model | [OIDC Issuer Model](#oidc-issuer-model) | Implemented | `identity_core__oidc_issuer`; keyed on canonical issuer host; minimal fields. `get_name()` is the `issuer_url` (no well-known catalog; `display_name` deferred — no backing field). |
| req-identity-core-organization | [Organization Model](#organization-model) | Implemented | `identity_core__organization`: a party that holds identities; role-free (customer/vendor/operator is a relationship asserted elsewhere); keyed on `name` in v0. |
| req-identity-core-human | [Human Model](#human-model) | Implemented | `identity_core__human`: one real person; every system's account for them points at it with the wildcard-source `HELD_BY_HUMAN__identity_core`; keyed on an operator-assigned `handle`. |
| req-identity-core-team | [Team Model](#team-model) | Implemented | `identity_core__team`: a group of people, keyed on a stable `handle`; role-free; no free-form blob. |
| req-identity-core-team-edges | [Team Edges](#team-edges) | Implemented | `BELONGS_TO_TEAM` (human or team to team, which is how teams nest) and `LEADS_TEAM` (human to team); no cardinality constrained. |
| req-identity-core-responsible | [Responsibility Stamp](#responsibility-stamp) | Implemented | `team.responsible` on any entity, whose value is a team's entity id; one owner per entity; open value set. |
| req-identity-core-email-address | [Email Address](#email-address) | Implemented | `identity_core__email_address`: one address, keyed by its canonical lower-cased form; holds no name; any plugin may write it. |
| req-identity-core-mailbox | [Mailbox](#mailbox) | Implemented | `identity_core__mailbox`: one display name as written, used with one address; keyed by both; its address is a hotlink to the address node. |
| req-identity-core-phone-number | [Phone Number](#phone-number) | Implemented | `identity_core__phone_number`: country code and national number apart; written only for a number stated with a country code. |
| req-identity-core-contact-edges | [Contact Edges](#contact-edges) | Implemented | Seven edges, one relationship each, outward from the record that states the fact; none carries a property. |
| req-identity-core-canonical-url | [Canonical Issuer URL](#canonical-issuer-url) | Implemented | One normalization spanning scheme'd/scheme-less forms; the convergence guarantee. |
| req-identity-core-issuer-id | [Deterministic Issuer Id](#deterministic-issuer-id) | Implemented | `oidc_issuer_id(raw)` over the canonical form; the sole id path. Namespace is the per-plugin `IDENTITY_CORE_NAMESPACE` (no repo-wide `TAP_NAMESPACE` constant exists; per-plugin is the convention). |
| req-identity-core-envelope | [Node Envelope Helper](#node-envelope-helper) | Implemented | `oidc_issuer_node_envelope(raw, *, dimensions=None)` returns the `{entity, node}` GRIFT fragment consumers merge. `display_name` param dropped — the spine projects `get_name()`=issuer_url, so a divergent name would be overwritten (honest v0 deviation). |
| req-identity-core-synthesis-general | [General-Case Synthesis](#general-case-synthesis) | Partial | Mechanism shipped (any observer *may* mint via the helper; github + samsite do). Order-independence (general-3) NOT fully realized in v0: aws_core has no enrichment phase, so the AWS-side TRUSTS_ISSUER link still relies on github's collector minting the singleton in the same run. |
| req-identity-core-existence-not-trust | [Existence Is Not Trust](#existence-is-not-trust) | Implemented | Node asserts reference/existence only; no trust field/default/edge. Trust is a separate explicit edge. |
| req-identity-core-edge-retargets | [Consumer Edge Retargets](#consumer-edge-retargets) | Implemented | github `ENABLED_ON` (source retargeted) + sigstore `IDENTITY_VOUCHED_BY` (target retargeted) stay with their asserting plugin. The generic `TRUSTS_ISSUER` (wildcard source) is owned by identity_core — trusting an issuer is cross-cloud, not AWS-specific; github's enrichment emits the instances. |
| req-identity-core-dimensions | [Dimension Strategy](#dimension-strategy) | Implemented | `identity.protocol: oidc` on the model default. |
| req-identity-core-deps | [Dependency Direction](#dependency-direction) | Implemented | Downward-only; declared in github/aws_core/sigstore_core/samsite `pyproject.toml` + `depends_on`. Only github + samsite import the helper (code dep); aws + sigstore are edge/vocabulary deps. |
| req-identity-core-migration | [Extraction & Migration](#extraction--migration) | Implemented | `github_core__oidc_issuer` → `identity_core__oidc_issuer`; id regenerates (collected, not seeded); samsite→github import killed. Old model dropped via a forward github `0004` DeleteModel (not a lineage rewrite). |
| req-identity-core-nongoals | [v0 Non-Goals](#v0-non-goals) | Implemented | Passkey/subject/credential nodes; issuer-metadata fetch; liveness; trust policy; well-known name catalog — all held out of v0. |

### Plugin Scope
----
RID: `req-identity-core-scope`

Status: `Implemented`

`identity_core` is a **library / substrate** plugin. Its v0 surface is two models
(`oidc_issuer`, `organization`), the issuer helper module (`identity_core.issuer`), and one generic
edge type (`TRUSTS_ISSUER__identity_core`, wildcard source). It registers its node
type, that edge type, and its dimensions at load; it ships **no collector** (`apps.py`
is `pass`; no `tap_cares` registration) and emits no edges itself. Consumers import
only from `identity_core.*`. The plugin is install-only: it stands up the vocabulary
and the minting mechanism that github_core, aws_core, sigstore_core, and samsite call
into (or point their edges at).

Teams (added 2026-10-20) add a fourth model, `team`, and two edges, `BELONGS_TO_TEAM` and
`LEADS_TEAM`, with the same posture: vocabulary only, no collector, nothing minted by the plugin
(`req-identity-core-team`, `req-identity-core-team-edges`).

### OIDC Issuer Model
----
RID: `req-identity-core-model`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__oidc_issuer"`, `ENTITY_NAME = "OIDC Issuer"`,
`ENTITY_DESCRIPTION = "An OpenID Connect identity provider (issuer)."` The node is the
convergence point for federated identity: it is referenced by github (issuer enabled
on a repo), AWS (a provider trusts it), and Sigstore (an entry is vouched by it).

Fields (carried forward from the github_core original, minus the well-known-name map —
see non-goals):

- `issuer_url` — the OIDC `iss` as observed (scheme'd when available); display/reference value.
- `host` — the canonical, scheme-less form (`req-identity-core-canonical-url`); the identity key and the value AWS IAM's provider `url` matches.
- `provider` — optional free-text provider label (e.g. `github-actions`), observed, non-authoritative.
- `configuration` — optional observed OIDC discovery metadata (JSON; described sub-keys when populated).
- `tags` — optional observed labels (JSON).

`CREATE_REQUIRED = ["issuer_url"]`. `get_name()` returns `issuer_url` (honest: for an
issuer we have no friendlier universal label), or an explicitly supplied per-node
`display_name` when a consumer provides one. Display: the amber/gold identity-anchor
palette (distinct from github-blue, AWS-beige, sigstore-green) — the hub all three
reference. The node carries `DEFAULT_DIMENSIONS = {"identity.protocol": "oidc"}`.

### Organization Model
----
RID: `req-identity-core-organization`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__organization"`, `ENTITY_NAME = "Organization"`. A party that
holds identities: a company, agency, or other body people act on behalf of. Added
2026-09-22 so an instance can place its customers on a design (highbar's landing diagram
draws "customers" as organizations); it is the first identity-holding party type, and it is
here rather than in any instance plugin because every identity-shaped plugin will want the
same node to hang users, groups and tenants from.

**Role-free.** The type says what the thing *is*, never what it is *to someone*. Customer,
vendor, assessor and operator are relationships another plugin asserts with an edge; the
same company is a customer in one instance and a vendor in another, and a type that bakes
one view in cannot be shared across them. This follows `req-identity-core-existence-not-trust`:
the substrate names the party and takes no position on its relationships.

Fields: `name` (required; display and v0 identity), `domain` (primary DNS domain when known;
blank = not observed). No free-form `configuration` field and no `tags` map: nothing collects an
organization's source record, so either would only collect unchosen data (`configuration` removed
2026-09-23; `tags` removed 2026-09-24, nothing read it).
`NATURAL_KEY = ("name",)`:
a designed organization often has no domain yet, so its name is the only fact it carries;
revisit when an observer supplies a stronger key. No default dimension: `identity.protocol`
does not apply, and a party-kind value would restate the entity type. Icon `organization`,
same identity-anchor palette as `oidc_issuer`.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-organization-1 | Name only | Implemented | A `create_node` write with only `name` succeeds; `domain` stays blank (not observed). |
| req-identity-core-organization-2 | Name required | Implemented | A write without `name` is refused. |
| req-identity-core-organization-3 | Role-free | Implemented | The type carries no default dimension and no field naming a role. |
| req-identity-core-organization-4 | No free-form blob | Implemented | A write carrying `configuration` is refused. |

### Human Model
----
RID: `req-identity-core-human`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__human"`, `ENTITY_NAME = "Human"`. One real person, independent of
any system they hold an account in. Added 2026-09-23 because the Okta, Duo and Teleport corpora
each model their own user and each left the cross-system link open-ended: without a neutral
node, "these four accounts are one person" cannot be said, and that join is most of what a
FedRAMP access review asks. George chose "human" over "person" (2026-09-23); Cartography's
equivalent node is also `Human`.

**The link is an edge, not a copied field.** `HELD_BY_HUMAN__identity_core` runs from any
account type to the human. Its source is wildcard, as `TRUSTS_ISSUER`'s is, so a vendor plugin
points at the human without identity_core depending on the vendor. Wildcard means the schema
accepts any source type, not only accounts, because nothing here can tell an account type from any
other; keeping the source an account is the drawer's job, and a traversal that needs accounts only
filters the source type. The edge asserts that two
records are the same person; it is drawn by whoever knows that (an operator seed, an HR feed, a
collector matching an immutable identifier) and never inferred from a display name or an email
address. An account with no such edge is unmatched, which an access review must be able to show.
Its one property, `matched_on`, records how the tie was made.
Cardinality is not constrained: an account pointing at more than one human is a *shared* account
(a break-glass login, a service account several people hold), which is itself an access-review
finding, so the graph records it rather than refusing it.

Fields: `handle` (required; the identity), `name` (display name; blank = not observed).
`NATURAL_KEY = ("handle",)`, declared and not unique, as every natural key is
(`req-grid-entity-natural-key-3`: two rows sharing a handle make the lookup refuse to choose): an identifier the operator assigns and keeps stable, such as an HR
employee number or the organization's canonical username. A name changes, and an email address
is an account attribute that is reassigned and aliased, so neither is identity. The type has no
free-form `configuration` field: there is no source payload to preserve, and a person record is
where unchosen personal data would collect. No default dimension. Icon `human`, the
identity-anchor palette.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-human-1 | Handle only | Implemented | A `create_node` write with only `handle` succeeds; `name` stays blank, and the display name falls back to the handle. |
| req-identity-core-human-2 | Handle required | Implemented | A write without `handle` is refused. |
| req-identity-core-human-3 | No free-form blob | Implemented | A write carrying `configuration` is refused. |
| req-identity-core-human-4 | Source unrestricted | Implemented | `HELD_BY_HUMAN__identity_core` accepts a source of any type (a non-account included) and a `matched_on` property; the spec and edge description say so. |
| req-identity-core-human-5 | Shared accounts are recorded | Implemented | One source may hold `HELD_BY_HUMAN__identity_core` edges to two humans, and both are queryable. |

### Team Model
----
RID: `req-identity-core-team`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__team"`, `ENTITY_NAME = "Team"`. A group of people who act together and answer for something together: a devops team, an engineering team, a company that contains them. Added 2026-10-20 (ruled by George): the vulnerability story needs a last link from a system to the people who manage it, and no node held the group. It is deliberately not an `organization`: an organization is a party that holds identities (a company or agency), and the demo has to show a team and a company side by side without a reader asking which is which. A team is the unit people join and leave, and it nests (`req-identity-core-team-edges`).

Role-free, like `organization`. What a team is responsible for is asserted elsewhere, by the ownership stamp (`req-identity-core-responsible`); a team type that said "devops" or "engineering" would bake one view in.

Fields: `handle` (required; the identity), `name` (display name; blank = not observed), `description` (what the team is for, in a sentence; blank = not observed). `NATURAL_KEY = ("handle",)`, declared and not unique (`req-grid-entity-natural-key-3`): an identifier the operator assigns and keeps stable, such as `devops` or `git-serious`. A name changes; a handle does not. The type has no free-form `configuration` field, for the reason `human` has none: there is no source payload to preserve, and a team record is where unchosen detail would collect. No default dimension. Icon `team`, the identity-anchor palette.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-team-1 | Handle only | Implemented | A `create_node` write with only `handle` succeeds; `name` and `description` stay blank, and the display name falls back to the handle. |
| req-identity-core-team-2 | Handle required | Implemented | A write without `handle` is refused. |
| req-identity-core-team-3 | No free-form blob | Implemented | A write carrying `configuration` is refused. |
| req-identity-core-team-4 | Role-free | Implemented | The type carries no default dimension and no field naming a kind of team or a responsibility. |
| req-identity-core-team-5 | Registered | Implemented | `identity_core__team` is declared in the manifest `[models]` table and `manage.py plugins` counts it. |

### Team Edges
----
RID: `req-identity-core-team-edges`

Status: `Implemented`

Two edges, both named as an action on the team they point at (`req-tap-plugin-edge-naming`; `aws_core` has `BELONGS_TO_ACCOUNT` as precedent).

- **`BELONGS_TO_TEAM__identity_core`**: source `identity_core__human` or `identity_core__team`, target `identity_core__team`; no properties. A human belongs to a team as a member. A team belongs to a team as a child of a parent. This one edge is both membership and hierarchy, so "everyone in the company" is a walk up from the people and "everyone under engineering" a walk down.
- **`LEADS_TEAM__identity_core`**: source `identity_core__human`, target `identity_core__team`; no properties.

Cardinality is not constrained, because the plugin's edge definitions carry none and a graph that records the situation is more useful than one that refuses it (as `HELD_BY_HUMAN` does for shared accounts). A person may belong to several teams, a team may have several parents, and a team may be led by two people. Leading does not imply belonging: a leader with no `BELONGS_TO_TEAM` edge is allowed, and a report may flag one. A cycle (team A inside team B inside team A) is not refused either; finding one is a read, not a write rule.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-team-edges-1 | Membership And Nesting | Implemented | `BELONGS_TO_TEAM__identity_core` accepts a `human` source and a `team` source, each to a `team` target, and a `human` can belong to a team that itself belongs to another team. |
| req-identity-core-team-edges-2 | Nothing Else Is Declared | Implemented | `BELONGS_TO_TEAM__identity_core` and `LEADS_TEAM__identity_core` declare `team` as the only target, and `LEADS_TEAM__identity_core` declares `human` as the only source. This is a declaration, not a write-time refusal: the grid's permission union admits an edge when either end's node type has no `OUTBOUND_EDGES`/`INBOUND_EDGES` of its own, and `human` and `organization` have none, so the declared constraint is what is asserted. |
| req-identity-core-team-edges-3 | Several Of Each Are Recorded | Implemented | One human with `BELONGS_TO_TEAM` edges to two teams, one team with two parents, and one team with two `LEADS_TEAM` edges each succeed and are queryable. |
| req-identity-core-team-edges-4 | Leader Need Not Be A Member | Implemented | A `LEADS_TEAM` edge from a human with no `BELONGS_TO_TEAM` edge to that team succeeds. |
| req-identity-core-team-edges-5 | Names Conform | Implemented | `validate_plugin` accepts both slugs under `req-tap-plugin-edge-naming`, and both edge descriptions state the cardinality and cycle rules above. |
| req-identity-core-team-edges-6 | Cycles And Second Leaders Reported | Backlog | A Search that lists teams on a cycle and teams with more than one leader. |

### Responsibility Stamp
----
RID: `req-identity-core-responsible`

Status: `Implemented`

An entity is stamped with the team answerable for it by the dimension key `team.responsible`, whose value is the **entity id of an `identity_core__team`**, as a lowercase hyphenated UUID string. The stamp is a dimension and not an edge because every entity on the grid would otherwise draw an edge to a handful of team nodes: hubs with thousands of inbound edges, and an edge type with a wildcard source for every kind of thing a team can own. A stamp is a string on the entity, indexed and queryable like any dimension (`req-grid-dimension-em`).

`team.responsible` is not in the `identity.*` namespace (`req-identity-core-dimensions`): the key is stamped on entities that have nothing to do with identity, and `identity.*` scopes identity vocabulary. It is a namespace of its own, `team.*`, whose first key this is; a later key such as `team.accountable` extends it.

One owner per entity: a dimension holds one value per key. The value set is open (a deployment has as many teams as it has), so the key's dictionary has one node, `team.responsible`, and no value nodes (the reasoning in `req-grid-dimension-reference`: a node per value suits closed sets only). The dictionary node is seeded by the instance that uses the key, not by this plugin. Because a team id is a plain string, a stamp naming a team that is deleted points at nothing and the grid does not notice; finding stamps with no live team is a read (`req-identity-core-responsible-4`).

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-responsible-1 | Value Is A Team Id | Implemented | The documented value of `team.responsible` is the entity id of an `identity_core__team`, lowercase and hyphenated, and the spec says so in one sentence beside the key. |
| req-identity-core-responsible-2 | One Owner | Implemented | An entity carries at most one `team.responsible` value; a second owner is a different key, not a second value. |
| req-identity-core-responsible-3 | Own Namespace | Implemented | The key sits in `team.*`, not `identity.*`, and the plugin sets it on no node by default. |
| req-identity-core-responsible-4 | Dangling Stamps Reported | Backlog | A Search that lists `team.responsible` values matching no live team. |
| req-identity-core-responsible-5 | RACI | Backlog | Accountable, consulted and informed (`team.accountable` and others) are not defined here; consulted and informed are many-valued and would need keyed dimensions or edges. |
| req-identity-core-responsible-6 | Team To Dimension Edge | Implemented | `ANSWERS_FOR_DIMENSION__identity_core` runs from an `identity_core__team` to a `dimension` node (for example `team.responsible`), carries no properties, and its description says the target is a dimension node. It records that a team answers under a key; the stamp itself stays a dimension on the entity. Cardinality is not constrained. |

### Email Address
----
RID: `req-identity-core-email-address`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__email_address"`, `ENTITY_NAME = "Email Address"`. One email address, independent of who uses it. Added 2026-11-13 (ruled by George 2026-11-11 and 2026-11-12).

The reason for the type is a join nothing made. An identity provider's user, a multi-factor user, a forge account, a cloud account's root contact, a commit's author line and a contact typed onto an application record all store an email as text on their own node. The address is the one value they share. As a node, "every record that names this address" is one hop, in any plugin, with no plugin depending on another.

It is not a person and does not claim one. An address is reassigned and aliased, which is why `identity_core__human` is keyed by a handle and never by an address (`req-identity-core-human`). Cartography's ontology says the same of its own join key: a normalised email is "not a unique identifier". A person is tied to an address by an edge someone had evidence for (`USES_EMAIL_ADDRESS`), never by a collector from the address alone.

Field: `address`, required, the identity. `NATURAL_KEY = ("address",)`. The canonical form is the address with surrounding space dropped and the whole of it lower-cased, defined once in `contact.canonical_email`. Nothing else is folded: dots and plus-tags mean different things at different providers, and folding them would merge strangers. Lower-casing the part before the `@` is itself a choice with a cost, accepted on purpose: SMTP lets a server treat that part as case-sensitive (RFC 5321 section 2.3.11), so `User@example.com` and `user@example.com` could in principle be two mailboxes, and here they are one node. In practice almost no server distinguishes them, while systems routinely store the same address in different case, so not folding would split one mailbox into several nodes far more often than folding merges two. A source's own spelling stays on the source's record. A write whose `address` is not already in that form is refused and never rewritten, so two observers cannot disagree about the key and every observer must call the one function. This follows the rule already used for issuers here (`req-identity-core-canonical-url`) and the convention agreed for address-like nodes across `computing_core` and this plugin: key on the canonical stored form, canonicalise in one place, and keep a source's own spelling on the source's own record.

The type holds no name. Three systems use three names with one address, so a single name on the address would be whichever writer came last; STIX 2.1's `email-addr` and UCO's address facet have exactly that shape and that problem. The name a system uses is on that system's account, or on a mailbox (`req-identity-core-mailbox`).

`contact.email_address_node(ref, raw)` returns the GRIFT node for an address, or None when the text is not one.

**Prior art, pinned.** Searched 2026-11-12. Standards: STIX 2.1 (OASIS, 2021-06-10), UCO 1.5.0, RFC 5322 and RFC 6532, vCard RFC 6350, tel URI RFC 3966, SCIM RFC 7643, schema.org V30.1, FOAF 0.99, W3C ORG (2014), OCSF 1.9.0, inetOrgPerson RFC 2798 and RFC 4519, and libphonenumber's `phonenumber.proto` (master). Tools: Cartography (current docs and 0.94.0), BloodHound CE and OpenGraph, Maltego's Standard Entities Catalog (2026-07-14), MISP's email object v19 and person object v21, SpiderFoot (master), JupiterOne, Microsoft Graph v1.0, git's mailmap and GitHub's commits API, Backstage. The investigation tools make the address a node (Maltego, SpiderFoot, STIX); the inventory graphs keep it a property and join on it (Cartography, BloodHound, JupiterOne). This plugin does both: the node here, and an account's own field hotlinked to it. None of the sources puts a name on a relationship. ITU-T E.164 itself was read only through summaries.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-email-address-1 | Keyed By The Canonical Address | Implemented | A write with a canonical `address` succeeds and the node's display name is the address; a write whose address is not in canonical form (upper case, surrounding space, a display name, not an address) is refused and nothing is written. |
| req-identity-core-email-address-2 | One Definition Of Canonical | Implemented | `contact.canonical_email` drops surrounding space and lower-cases the whole address, the part before the `@` included; it folds nothing else and returns None for text that is not one address. The check is on shape, not deliverability: one `@`, a local part with no leading, trailing or doubled dot, and a domain of labels made of letters, digits and inner hyphens. A quoted local part and an address literal are not accepted. The model validates with the same function. Two addresses that differ only in case are therefore one node, by decision. |
| req-identity-core-email-address-3 | No Name | Implemented | A write carrying `name` is refused. |
| req-identity-core-email-address-4 | Not A Person | Implemented | The type has no edge to a human that a collector draws from the address alone; `USES_EMAIL_ADDRESS` is drawn by an operator or a matcher. This is a rule on writers, stated in the edge's description, not a write-time refusal. |

### Mailbox
----
RID: `req-identity-core-mailbox`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__mailbox"`, `ENTITY_NAME = "Mailbox"`. One display name as it was written, used with one email address: `George Chamales <george@example.com>`. RFC 5322 defines that pair and calls it a mailbox (`mailbox = name-addr / addr-spec`; `name-addr = [display-name] angle-addr`). Added 2026-11-13 (ruled by George 2026-11-12, after the prior-art search above).

Why it is a node. The first design put the name on the edge from a record to the address. George's rule: an edge is lightweight, and wanting to put context on one usually means a node is missing. The missing node is the pair. It is not a property of the address, for the reason above, and it is a recognised unit in the field: a git commit's author and committer are each one, `.mailmap` maps one pair to another, OCSF keeps `from_mailbox` beside the bare `from`, and MISP's email object pairs `from` with `from-display-name`. So a record points at a mailbox with an edge that carries nothing, and the mailbox points at its address.

Where this goes further than the field, stated plainly: every source above that has the pair keeps it inside the record that used it. Lifting it out into a node that several records share is this plugin's own step. It is taken because a commit's author cannot be an account, there are too many commits to give each a contact node of its own, and one type to search by name across every source is the point.

What does not need one: an account. A system's own user record is already the node for the party it names. It carries its own name and points at the address directly (`REGISTERED_WITH_EMAIL`). A mailbox is for a party a record names and has no node for.

Fields: `address` (the canonical address, as on the address node) and `display_name` (the name exactly as written, less surrounding space; not blank, no control character). `NATURAL_KEY = ("address", "display_name")`. Two spellings of a name at one address are two mailboxes on one address node; nothing merges them and nothing is overwritten. A name with no address makes no mailbox: a name alone as a key would merge every John Smith, so it stays a field on the record that stated it.

`address` is a hotlink (`HOTLINKS`, mode `exact`, to `DELIVERS_TO_ADDRESS`): the field and the edge to the address node must agree, so a mailbox cannot be written naming an address it has no edge to, and the edge cannot outlive the field. This is the first hotlink declared in a plugin. `contact.mailbox_fragment(ref, display_name, raw_address)` returns the address node, the mailbox node and the edge with its hotlink data, for one batch.

A person is tied to a mailbox with the existing `HELD_BY_HUMAN`, whose source is unrestricted.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-mailbox-1 | The Pair Is The Key | Implemented | Two mailboxes with one address and two names are two nodes on one address node; the same pair written twice is one mailbox, one address and one edge. |
| req-identity-core-mailbox-2 | Address And Edge Agree | Implemented | A mailbox written with no `DELIVERS_TO_ADDRESS` edge, or with an edge naming another address, is refused whole. |
| req-identity-core-mailbox-3 | Canonical Address, Name As Written | Implemented | An address not in canonical form, a padded or empty name, a missing name and a missing address are each refused. |
| req-identity-core-mailbox-4 | One Fragment Writes It | Implemented | `contact.mailbox_fragment` yields the address node, the mailbox and the edge, and importing it succeeds; it returns None when either the name or the address is unusable. |
| req-identity-core-mailbox-5 | Nothing Is Carried On An Edge | Implemented | `NAMES_CONTACT_MAILBOX` and `DELIVERS_TO_ADDRESS` declare no property. The hotlink data on `DELIVERS_TO_ADDRESS` is the grid's own, validated by the grid, and holds only the address the field already holds. |

### Phone Number
----
RID: `req-identity-core-phone-number`

Status: `Implemented`

`ENTITY_TYPE = "identity_core__phone_number"`, `ENTITY_NAME = "Phone Number"`. One phone number, with its country code and its national number as separate fields. Added 2026-11-13 (ruled by George 2026-11-12: "we should always have a field for country code, separate from the in-country code").

A number with a country code identifies one line anywhere, which is what makes a shared node safe. A number without one does not: "555-0100" means something only inside a country nobody named. The tel URI standard says so directly (RFC 3966: "Local numbers MUST have a 'phone-context' parameter that identifies the scope of their validity"), and libphonenumber refuses to parse one unless told a default region. So no country code is ever assumed, and a number stated without one is never written as this type. It stays on the record that stated it, with the country code null, meaning never sent, until one is known. Writing it here with a null country code would also be wrong mechanically: a null in a natural key means the row cannot be found again, so every run would write another.

Fields: `country_code` (1 to 3 digits, no plus sign), `national_number` (digits), `extension` (digits, or the empty string when there is none). `NATURAL_KEY = ("country_code", "national_number", "extension")`. The empty extension is a value, not a gap, so a number with none is still found again, and a desk line and its switchboard are two nodes.

How long a country code is follows from a number's leading digits: zones 1 and 7 have one-digit codes, a fixed list has two, and every other code has three. The type checks that `country_code` has the length its own digits imply and that the whole number is at most 15 digits. It does not check that a code is assigned to a country; that list changes and is not kept here.

The text as typed and how the country code came to be known are facts about one statement of a number, and belong on the record that made it. `contact.parse_phone(raw)` returns both with the split (`raw`, and `source`: `plus_sign` when the text was in international form, `not_given` otherwise), so a stating record can store them. This is libphonenumber's model (`raw_input`, `country_code_source`) without its region inference. `contact.phone_number_node(ref, phone)` returns the node, or None when the number has no country code.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-phone-number-1 | Country Code And Number Apart | Implemented | A number in international form is split at its country code for one-, two- and three-digit codes; separators are dropped; an extension is kept apart. |
| req-identity-core-phone-number-2 | No Country Code Is Ever Assumed | Implemented | Text with no leading plus parses to a number with `country_code` None and `source` `not_given`, and `phone_number_node` returns None for it. |
| req-identity-core-phone-number-3 | Only A Whole Number Is Written | Implemented | A write with no country code, a code with a plus sign, a code of the wrong length for its digits, a leading zero, non-digits, or more than 15 digits in all is refused. |
| req-identity-core-phone-number-4 | Extension In The Key | Implemented | The same number with and without an extension is two nodes; a number written with no extension has `extension` empty. |
| req-identity-core-phone-number-5 | Assigned Codes Not Checked | Backlog | Whether a country code is assigned is not checked. A list would need a pinned source and an update path. |

### Contact Edges
----
RID: `req-identity-core-contact-edges`

Status: `Implemented`

Seven edges, one relationship each, each running outward from the record that states the fact, and none carrying a property (`req-identity-core-mailbox`, on why).

- **`DELIVERS_TO_ADDRESS__identity_core`**: `mailbox` to `email_address`. The mailbox's own address, mirrored by its hotlink.
- **`REGISTERED_WITH_EMAIL__identity_core`**: any source to `email_address`. The address on an account's own record. An account that keeps the address as a field declares the field as a hotlink to this edge.
- **`USES_EMAIL_ADDRESS__identity_core`**: `human` to `email_address`. Drawn by an operator or a matcher, not by a collector.
- **`NAMES_CONTACT_MAILBOX__identity_core`**: any source to `mailbox`. A record names this mailbox as its contact.
- **`REGISTERED_WITH_PHONE__identity_core`**: any source to `phone_number`. The number on an account's own record.
- **`NAMES_CONTACT_PHONE__identity_core`**: any source to `phone_number`. The number a record gives for its contact.
- **`NAMES_CONTACT_ORGANIZATION__identity_core`**: any source to `organization`. The organization a record gives for its contact. The organization is found by name, the only key that type has, so two spellings are two organizations.

"Any source" is a wildcard, as on `HELD_BY_HUMAN` and for the same reason: a vendor plugin's type can point here without this plugin depending on it. Each edge has an empty identity discriminator list, so the same relationship written twice is one edge.

A source declared on an edge is a declaration and not a write-time refusal: the grid does not yet refuse an edge from a type the definition does not list (`unified-systems-com/tap#397`). `USES_EMAIL_ADDRESS` from something other than a human is therefore accepted today.

The author and committer of a commit are two more relationships of this kind (commit to mailbox). They belong to the plugin that owns the commit type and are not declared here.

#### Acceptance Criteria

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-contact-edges-1 | Each Is Accepted | Implemented | Each of the seven edges is written between a source and its target type. |
| req-identity-core-contact-edges-2 | No Properties | Implemented | Every one declares an empty property schema. |
| req-identity-core-contact-edges-3 | Written Twice Is One Edge | Implemented | A mailbox fragment imported twice leaves one `DELIVERS_TO_ADDRESS` edge. |
| req-identity-core-contact-edges-4 | Names Conform | Implemented | `validate_plugin --strict` accepts all seven slugs. |
| req-identity-core-contact-edges-5 | Declared Sources Enforced | Backlog | An edge from a source its definition does not list is refused, once the grid enforces declared sources. |

### Canonical Issuer URL
----
RID: `req-identity-core-canonical-url`

Status: `Implemented`

`canonical_issuer_url(raw)` defines the **single** canonical form so independent
observers converge. It:

1. strips the scheme (`https://` / `http://`),
2. lowercases the host,
3. strips a trailing slash,
4. preserves any path (the `iss` may carry one).

The result (e.g. `token.actions.githubusercontent.com`) is the identity key. Both
github's scheme'd `iss` and AWS IAM's scheme-less provider `url` normalize to the same
value. This is the convergence guarantee: it lives in one function, not duplicated
across collectors. (Scheme is intentionally dropped from the *key* because AWS stores
none; the scheme'd `iss` is retained as the `issuer_url` display field.)

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-canonical-url-1 | Scheme-spanning | Implemented | Scheme'd and scheme-less inputs for the same issuer normalize to one key. |
| req-identity-core-canonical-url-2 | Single definition | Implemented | Exactly one implementation; consumers call it, never re-implement normalization. |
| req-identity-core-canonical-url-3 | Path-preserving | Implemented | A path in the `iss` is preserved (issuers may carry one); only scheme/case/trailing-slash are normalized. |

### Deterministic Issuer Id
----
RID: `req-identity-core-issuer-id`

Status: `Implemented`

`oidc_issuer_id(raw) -> UUID` is `uuid5(TAP_NAMESPACE, "identity_core__oidc_issuer:" +
canonical_issuer_url(raw))`. It is the **only** sanctioned way to compute an issuer
entity id. No consumer may hardcode an id or re-derive it from a different string —
that is the collector-identity-fragility lesson (a type/string rename silently breaks
hardcoded uuid5s). Because the id keys on the canonical form, github and AWS produce
the same id and their nodes merge; because it is a pure function of the URL, the node
is idempotent across runs and observers.

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-issuer-id-1 | Canonical-keyed | Implemented | Id derives from `canonical_issuer_url`, so scheme'd/scheme-less inputs give one id. |
| req-identity-core-issuer-id-2 | Sole path | Implemented | All consumers obtain the id from this helper; none hardcode or re-derive it. |
| req-identity-core-issuer-id-3 | Idempotent | Implemented | Repeated synthesis of the same issuer yields the same node; no duplicates. |

### Node Envelope Helper
----
RID: `req-identity-core-envelope`

Status: `Implemented`

`oidc_issuer_node_envelope(raw, *, dimensions=None, display_name=None)` returns a GRIFT
node fragment (entity id from `oidc_issuer_id`, `entity_type =
identity_core__oidc_issuer`, `issuer_url`/`host` populated from `raw` +
`canonical_issuer_url`) that a consumer merges into its own GRIFT batch. It is the
minting mechanism referenced by `req-identity-core-synthesis-general`. Consumers supply
their own dimensions/anchor context; the helper does not write to the grid itself
(no parallel mutation path — GRIFT flows through the caller's normal batch).

### General-Case Synthesis
----
RID: `req-identity-core-synthesis-general`

Status: `Partial`

Issuer nodes are synthesized **generally**, by any observer, never seeded. There is no
well-known-issuer catalog and no boot-time seed record for issuers. A collector that
encounters an issuer URL — github reading its Actions issuer, aws reading its IAM OIDC
provider `url`, samsite reading a verification policy's `oidc_issuer` — mints the node
via `oidc_issuer_node_envelope` and merges it. Convergence is automatic: all observers
of the same issuer produce the same id (`req-identity-core-issuer-id`) and merge.

The **mechanism** is fully in place: the helper is the single mint path and any observer
may call it. Two of the three observers do — github's collector mints the singleton, and
samsite's compliance collector mints from the verification policy's issuer, both through
the shared helper, and they converge by id. **aws does NOT mint in v0**: aws_core's boto3
collector is single-phase with no grid-link engine, so the AWS-side `TRUSTS_ISSUER` link
is still resolved by github_core's enrichment, which relies on github having minted the
issuer earlier in the same run. So the **run-order hazard is reduced but not eliminated**
in v0 — general-3 below is Deferred until aws_core grows its own issuer-minting (or an
enrichment phase). This is the honest state; the vocabulary now lives where aws *could*
mint from without reaching into github.

| ACID | Title | Status | Description |
| --- | --- | :---: | --- |
| req-identity-core-synthesis-general-1 | No seed | Implemented | No boot record or seed data creates issuer instances; identity_core ships mechanism only. |
| req-identity-core-synthesis-general-2 | Any observer mints | Implemented | Every consumer that sees an issuer URL can synthesize the node via the helper; github + samsite do. |
| req-identity-core-synthesis-general-3 | Order-independent convergence | Deferred | NOT realized in v0: aws_core has no minting/enrichment path, so the AWS TRUSTS_ISSUER link still depends on github's same-run synthesis. Realized when aws mints the issuer from its own observation. |

### Existence Is Not Trust
----
RID: `req-identity-core-existence-not-trust`

Status: `Implemented`

The presence of an `oidc_issuer` node conveys only that an issuer identity was
referenced by some observer. It is **not** an assertion that the issuer exists in the
world, is reachable, or is trusted by anyone. Trust and relationship semantics live
exclusively on explicit edge **instances** created by an emitter (`TRUSTS_ISSUER`,
`IDENTITY_VOUCHED_BY`, `ENABLED_ON`). identity_core defines no trust field and no trust
default, and — though it owns the generic `TRUSTS_ISSUER` edge *type* (schema) — it
never creates a trust *instance*: a trust edge exists only when some emitter (in v0,
github's enrichment) writes one. Owning the type is vocabulary, not an assertion. A
consumer reasoning about trust must follow an explicit trust edge, never infer it from
node existence.

### Consumer Edge Retargets
----
RID: `req-identity-core-edge-retargets`

Status: `Implemented`

Each consumer retargets its issuer-touching edge to `identity_core__oidc_issuer`. Edge
ownership follows one rule: a **domain-specific** assertion stays with the plugin that
asserts it; a **generic, cross-plugin** relationship is owned by the substrate with a
wildcard source (so no upward dep — the same pattern as compliance_core's wildcard-
source edges).

- **github_core — `ENABLED_ON`** (`oidc_issuer → github_repository`): domain-specific (a github_app / github's issuer enabled on a github repo). Stays in github; retarget the source type.
- **identity_core — `TRUSTS_ISSUER`** (`* → oidc_issuer`): **generic.** "A principal trusts an OIDC issuer" is a cross-cloud federation relationship (AWS IAM providers, GCP workload-identity pools, Azure federated credentials, k8s/Vault JWT trust) — not AWS-specific. So the substrate owns the one generic type (`TRUSTS_ISSUER__identity_core`) with a **wildcard source** rather than one `TRUSTS_ISSUER__<cloud>` per principal. A constrained source would reference a domain type and make identity_core depend *upward* — the wildcard is what makes substrate ownership possible. github's enrichment emits the AWS instances in v0; aws_core owns nothing here (no dep on identity_core).
- **sigstore_core — `IDENTITY_VOUCHED_BY`** (and any other issuer-referencing sigstore edge, e.g. `ATTESTED_BY` where it anchors the issuer): domain-specific (a *rekor log entry* vouches). Stays in sigstore; retarget the target type.

Endpoint constraints on these edges reference `identity_core__oidc_issuer`; where an
edge should accept any workflow/source (Bucket-1 wildcard precedent), it stays wildcard.

### Dimension Strategy
----
RID: `req-identity-core-dimensions`

Status: `Implemented`

The model default dimension is `{"identity.protocol": "oidc"}`, establishing the
`identity.*` dimension namespace as the home for identity-vocabulary scoping. Future
identity node types (deferred, see non-goals) extend this namespace rather than
inventing sibling ones.

### Dependency Direction
----
RID: `req-identity-core-deps`

Status: `Implemented`

identity_core depends on nothing above core (`tap_grid`/`tap` only). Consumers depend
**downward** on it: `github_core`, `aws_core`, `sigstore_core`, and `samsite` declare
`identity-core-tap` in `pyproject.toml` and list `identity_core` in their
`depends_on`. The AST import-graph guard (`tap/plugin_deps.py`) enforces that the
`from tap_plugin.identity_core...` imports are declared. The `samsite →
github_core` issuer import is deleted in the same change (samsite imports
`identity_core.issuer` instead).

### Extraction & Migration
----
RID: `req-identity-core-migration`

Status: `Implemented`

The move renames `github_core__oidc_issuer` → `identity_core__oidc_issuer`. That
changes the `entity_type` string and therefore the `uuid5`-derived issuer id — but the
issuer node is **collected** (re-produced each run via the envelope helper), not a
static seed, so it regenerates cleanly on the next collection (contrast the
uuid5-hash-token-fallout that bit a *static seed*). Steps:

As-built steps:

1. Stood up `identity_core`: `OidcIssuer` model + `identity_core.issuer` helper module + `0001_initial`.
2. Moved the id/normalization/envelope logic into `identity_core.issuer` (`canonical_issuer_url` is new — it did not exist before; github keyed the id on the raw scheme'd URL, samsite host-normalized ad hoc). github's collector + samsite's `sigstore_link` now call the shared helper. `github_core.collectors.github_collector.identity.oidc_issuer_id` was removed.
3. Dropped `github_core/models/oidc_issuer.py` via a **forward** `github_core/0004` `DeleteModel` (the create-then-drop lineage is left intact rather than rewritten — standard, and migrations squash on eviction anyway). Updated `spec-github-core-v0.md` (7 models, 8 edges).
4. Retargeted consumer edges (`req-identity-core-edge-retargets`) and made `TRUSTS_ISSUER` a generic `identity_core`-owned edge (`TRUSTS_ISSUER__identity_core`, **wildcard source**) rather than one type per cloud. The `aws_oidc_provider_trusts_issuer` **enrichment rule stays in github's manifest** (edge types resolve globally, so github may emit an identity_core-owned type; aws_core has no enrichment engine to host the rule) — only its `edge_type`/`target_entity_type` strings + comment changed. aws_core ends up with **no dependency on identity_core** (it neither owns nor references the edge).
5. Replaced the `samsite → github_core` issuer import with `identity_core.issuer` (samsite's `sigstore_link` wrappers now delegate to it).
6. Updated the github enrichment rule's comment to the new architecture (issuer vocabulary in identity_core; github still mints the singleton in v0, so the same-run ordering note is honest, not obsolete — general-3 is Deferred).
7. Registered identity_core in `boot/test_all.boot.json` (install-only, ordered before its consumers).

Ordering: this is namespace churn (a new `entity_type`, a new edge owner), so it landed
**before eviction** freezes the plugins at released tags; otherwise the rename would have
become a coordinated multi-repo re-tag across identity_core + github + aws + sigstore +
samsite. (The evicted-tag demo profile `boot/samsite.boot.json` still references the old
world; it resyncs at plugin re-release, like the compliance_core extraction before it.)

### v0 Non-Goals
----
RID: `req-identity-core-nongoals`

Status: `Implemented`

Explicitly out of scope for v0:

- **Passkey / subject / credential identity nodes.** TAP does not model its own
  passkey/authenticator implementation on the grid in v0 (auth lives sub-grid). When
  such nodes are wanted, identity_core is their natural home and extends the
  `identity.*` namespace — but nothing is built for them now.
- **Issuer-metadata fetch / discovery.** No network call to `/.well-known/openid-configuration`; `configuration` is populated only from what a collector already observed.
- **Issuer liveness / reachability.** The node makes no claim the issuer is reachable.
- **Trust policy.** No trust fields, defaults, or edges (`req-identity-core-existence-not-trust`).
- **Team policy** (2026-10-20). No team types or roles beyond lead and member, no enforcement that a team hierarchy is acyclic or a team has one leader, no RACI beyond `team.responsible`, and no personal data on a person or team record.
- **Well-known name catalog.** The github_core original hardcoded a
  `_WELL_KNOWN_NAMES` map (`token.actions.githubusercontent.com` → "GitHub Actions
  OIDC"). It is **dropped**: it is the same special-case-the-known-issuer pattern at the
  cosmetic layer, and it fails the "don't assume other issuers exist" test. The node's
  name is its `issuer_url` (or a consumer-supplied `display_name`), honest for every
  issuer including unknown ones.
