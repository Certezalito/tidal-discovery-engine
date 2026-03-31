# Data Model: Documentation Overhaul

## Entities

### ReadmeSection
Represents one top-level README content section in the required order.

| Field | Type | Required | Description |
|---|---|---|---|
| id | string | Yes | Stable identifier (`setup`, `modes`, `all-parameters`, `troubleshooting`, `scheduling`). |
| title | string | Yes | Human-readable section title in README. |
| order_index | integer | Yes | Position in top-level section ordering. |
| scope | enum | Yes | `quick-start`, `reference`, or `operations`. |
| content_rules | list[string] | Yes | Required content constraints for this section. |

Validation rules:
- `order_index` values must be contiguous and unique for top-level sections.
- Top-level order must exactly match: Setup -> Modes -> All Parameters -> Troubleshooting -> Scheduling.
- Section guidance must not duplicate normative content from another top-level section.

### UsageExample
Represents a runnable CLI example embedded in README.

| Field | Type | Required | Description |
|---|---|---|---|
| scenario_id | string | Yes | Unique scenario identifier (for traceability in reviews). |
| mode | enum | Yes | Mode context (`mode1`, `mode2`, `mode3`). |
| command | string | Yes | Executable CLI command example. |
| expected_outcome | string | Yes | Plain-language expected result. |
| option_notes | list[string] | No | Notes for required option combinations or caveats. |

Validation rules:
- Every supported mode must include at least one `UsageExample`.
- Command strings must be syntactically valid for current CLI flags.

### FailureGuidanceEntry
Represents one troubleshooting entry for a user-visible failure category.

| Field | Type | Required | Description |
|---|---|---|---|
| failure_code | string | Yes | Stable failure category identifier. |
| symptoms | string | Yes | What users observe when failure happens. |
| explanation | string | Yes | Why the behavior occurs. |
| corrective_action | string | Yes | Actionable recovery step users can take. |
| fallback_behavior | string | No | Explicit fallback/no-fallback behavior statement. |

Validation rules:
- `symptoms`, `explanation`, and `corrective_action` are mandatory for every entry.
- Entry must use plain language and avoid implementation-only jargon.

### DocsUpdateChecklistItem
Represents one maintainer verification item in docs update checklist.

| Field | Type | Required | Description |
|---|---|---|---|
| checklist_id | string | Yes | Stable checklist item ID (`DOC-001`, etc.). |
| section_target | string | Yes | README section that must be reviewed/updated. |
| verification_rule | string | Yes | Condition that defines completion. |
| status | enum | Yes | `pending` or `done` in review workflow. |

Validation rules:
- Checklist must cover all top-level README sections.
- Checklist completion requires at least one reviewer confirmation.

## Relationships

- `ReadmeSection` contains `UsageExample` entries and may include `FailureGuidanceEntry` items.
- `DocsUpdateChecklistItem` references one or more `ReadmeSection` IDs as review targets.

## State Transitions

1. Define required section architecture and content boundaries.
2. Populate/refresh usage examples by mode.
3. Add or update troubleshooting entries in structured prose format.
4. Run checklist validation for section coverage and consistency.
5. Complete maintainer peer review and mark checklist items done.
