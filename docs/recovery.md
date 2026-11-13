**Reconstruction example — explanatory weighted score:**

```text
score(record, scenario) = sum(weight_j × normalized_value_j(record))
```

This is a starting model, not a claim that one scalar score captures all decisions. Explicit constraints should determine eligibility before ranking. The interface should reveal missing evidence and tradeoffs.

### 15.3 Avoid filter-induced ranking surprises

If normalization is recalculated on every filtered subset, an unchanged record can acquire a different score merely because the user hid its competitors. Prefer an explicit reference population and show when it changes.

Store the normalization basis, weights, criteria, constraints, missing-value handling and dataset version as part of the scenario. Show the difference between a descriptive association and evidence for a causal decision.

### 15.4 More distinctive features

- **Robustness envelope:** show how often an alternative remains preferred across plausible weights.
- **Counterexample explorer:** identify nearby alternatives that reveal a recommendation's weakest assumption.
- **Disagreement view:** compare two users' scenarios criterion by criterion.
- **Evidence dossier:** export the selected cohort, source evidence, assumptions and sensitivity results.
- **Constraint debugger:** explain which condition excluded an alternative.

These proposals reuse cohorts, variable mappings and versioned analyses rather than adding a disconnected scoring page.

## 16. Other proposed differentiators

### 16.1 Refresh Observatory

Compare API refreshes or imported versions: new/removed records, field drift, category changes, missingness changes and shifts in previously saved cohorts. Let users review changes before activating a refreshed version.

### 16.2 Evidence Graph

Represent relationships between records, entities and evidence where the source supplies them. Connect graph selection to the same table/Keshif cohort. Preserve source/provenance and distinguish extracted, asserted and inferred relationships.

### 16.3 Review cohorts

Turn a selection into a small review workflow: annotation, adjudication, disagreement and version-aware completion. This provides useful human labels for evaluating semantic clusters and decision criteria before introducing more automation.

## 17. Reconstruction sequence and acceptance criteria

The work should be restored in reviewable increments, with a source snapshot after each coherent milestone.

### Step 1 — Recover and reconcile specifications

Obtain the actual `datalab-explorer-specifications.md` and original adaptation report if available. Reconcile this report against them. Keep unknown requirements visible rather than silently filling gaps.

**Accept when:** every specification section has an implemented/proposed/deferred status and a test or review criterion.

### Step 2 — Restore the core application

Rebuild the Flask factory, persistence, account CLI, project model, imports, versioning, preparation, field mapping and API worker. Restore the TypeScript build and linked Keshif/table workspace.

**Accept when:** setup is reproducible, a fixture dataset can be imported/prepared/versioned/explored/exported, and core contract tests pass.

### Step 3 — Separate Keshif from examples

Copy and checksum the necessary distribution/assets, preserve licenses and canonical source, point the build exclusively at vendor files, then remove archives.

**Accept when:** a clean build and browser run succeed without an `archives/` directory.

### Step 4 — Restore roles and schema migration

Add schema version 2 and central access checks. Restore membership UI and role-aware project listings.

**Accept when:** viewer/editor/owner contract tests pass, including direct HTTP mutations, downgrade/removal, owner protection and a real version-1 migration fixture.

### Step 5 — Restore reviewed publication

Implement projection, profile recomputation, config sanitization, preview digest, explicit confirmation, frozen storage, anonymous reader and revocation.

**Accept when:** no private fields, samples, annotations, paths, source settings or IDs leak; a stale review fails; anonymous private access fails; all revoked endpoints return 404; private edits do not mutate published data.

### Step 6 — Restore French localisation

Rebuild shared catalog and static-template translation, server feedback and Keshif locale integration. Preserve drafts, active version and exact selection on language changes.

**Accept when:** browser tests verify both languages while source values and leading-zero identifiers remain unchanged.

### Step 7 — Resolve the final UI and runtime questions

Investigate the public gray overlay and French native facet interaction. Rerun the malformed-input test. Restart web/worker against a backed-up database and verify health, migration version, public 404 behavior and built manifest.

**Accept when:** final test logs and screenshots are exported, services serve the intended build, and unresolved limitations are documented.

### Step 8 — Publish a durable development state

Create a reviewable commit and preserve a downloadable patch/source archive. Update setup/start instructions and validation documentation to the actual final results.

**Accept when:** another clean checkout can reproduce the application without relying on a cloud session's untracked files.

### Step 9 — Prototype additional labs

Start with precomputed semantic coordinates and a small transparent decision scenario. Measure usability, language/domain quality and integration complexity before committing to model infrastructure.

**Accept when:** selections remain linked, provenance is reproducible, and no new feature bypasses project/publication access rules.

## 18. Handoff inventory

### Previously implemented, according to the retained record

- Flask/TypeScript studio foundation and API worker.
- Imports, ETL recipes, field mappings and immutable dataset versions.
- Keshif exploration, record table/inspector, saved dashboards/cohorts and exports.
- Independent retained Keshif runtime and archive removal.
- Owner/editor/viewer collaboration.
- Reviewed immutable public releases with projection and revocation.
- Separate anonymous reader.
- French application/table/common-Keshif/server localisation.
- Schema-2 migration and expanded Python/browser coverage.
- Researched semantic atlas and decision studio proposals.

### Explicitly unfinished or unverified

- Final additional malformed-input test result.
- Final French public native-facet/gray-overlay diagnosis.
- Final full-suite run after the last changes.
- Live web/worker restart and main schema-2 verification.
- Final validation/setup documentation refresh and environment-draft save.
- Live OpenAlex harvesting under an allowed network policy.
- Durable implementation commit/push or full source export.

### Available now

This Markdown report and the original example repository. The implementation source, former screenshots and final logs were not recovered in the accessible workspace. This document preserves enough architectural and behavioral detail to guide reconstruction, while keeping that limitation explicit.