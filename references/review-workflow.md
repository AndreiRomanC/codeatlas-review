# Spec-grounded review workflow

Use this reference when producing a review.

## Evidence order

1. Applicable specification text and its revision/provenance.
2. Target implementation and directly required dependencies.
3. Selected CodeAtlas references with exact provenance.

Do not convert reference consensus into a requirement. If references agree with one another but conflict with the specification, report both the specification violation and the historical consensus as an implementation-drift signal.

If the specification is unavailable, state that the review is incomplete. Findings may still describe implementation defects, risks, and reference differences, but must not be labeled specification violations.

When a local `.txt` specification reports `revision_verified: false`, use its content but disclose that CodeAtlas could not independently confirm the requested revision. Do not silently present the filename or folder location as authoritative revision metadata.

## Progressive retrieval

- Level 1: search metadata only.
- Level 2: retrieve normally 2–4 selected entities or artifacts.
- Level 3: retrieve additional callees, data definitions, or configuration only when needed to resolve a concrete question.

Prefer references that cover distinct revisions or variants. Same-hash occurrences establish reuse; same-name/different-hash candidates are useful for drift analysis.

## Report structure

Use these sections and omit none; write `None identified` or explain missing evidence where appropriate:

1. Summary
2. Specification findings
3. Defects / risks
4. Reference comparison
5. Implementation drift / inconsistencies
6. Uncertainties / missing information
7. Recommended checks

For each reference observation include repository, revision, path, entity name, line range, and hash when available. Clearly distinguish facts from inferences.
