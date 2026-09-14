<!--
Sync Impact Report:
- **Version Change**: 1.10.0 → 1.11.0
- **Modified Principles**: Principle X (Critical Dependency Currency & Capability Discovery) — amended to mandate updating the required version file (`pyproject.toml`) when new functionality in critical client libraries (e.g., `tidalapi`) is identified and adopted.
- **Added Principles / Sections**: None (amended Principle X, Technical Standards & Workflow Quality Gate, and Compliance Review Expectations)
- **Removed Sections**: None
- **Templates requiring updates**: None
- **Follow-up TODOs**: None
-->
# Tidal Discovery Engine Constitution

## Core Principles

### I. User-Centricity & Understandability
The project MUST prioritize a simple and intuitive command-line interface (CLI) and
supporting documentation that is easy to understand for end-users. Configuration
MUST remain minimal, usage MUST be straightforward, and every feature change MUST
include clear usage examples and behavior notes in end-user documentation. Any changes to
CLI options, arguments, or system default parameter values MUST be documented in the
README. Unknown facts MUST NOT be guessed. They MUST be marked explicitly and resolved
from the best available authoritative source, preferring repository documentation first and
then official vendor or API documentation when the repo does not contain the answer.

Rationale: Users can only benefit from automation when behavior is discoverable and
explainable without source-code inspection. Undocumented default changes create confusion
and break user expectations across updates.

### II. Automation
The core value lies in automating the process of finding new music and creating
playlists, saving the user time and effort. Workflows MUST be designed to run
without manual intervention once configured (for example, scheduler/cron usage).

### III. Personalization
By starting with the user's favorite tracks, generated playlists MUST be tailored to
specific musical tastes. Algorithms and integrations MUST respect and leverage user
data to maximize relevance.

### IV. Extensibility
The project MUST use a modular design so other music services or recommendation
engines can be accommodated in the future. Code MUST remain loosely coupled and
interfaces MUST be clearly defined.

### V. Reliability & Verifiability
The application MUST include robust error handling and logging to ensure consistent,
predictable behavior, especially when running as a scheduled task. Failures MUST be
handled gracefully and logged for diagnosis. Every behavior-changing code path MUST
have targeted automated validation that can fail if the behavior regresses.

### VI. AI Cost & Token Efficiency
When talking with AI services like Gemini, prompts MUST restrict generated output to the
bare minimum required for the task. This minimizes token output and overall operational
cost.

Rationale: Extraneous output from AI models increases costs and latency without adding
value to the automated playlist generation workflow.

### VII. Local Caching & Performance Efficiency
External metadata, AI track classifications (such as genres), and heavy API search results
MUST be cached locally in structured persistent storage (e.g., SQLite or database) to
minimize redundant API requests, reduce execution latency, and eliminate unnecessary AI costs
across repeated runs. Caches MUST support re-checking or invalidating unknown/unclassified items
to ensure progressive quality improvements while maintaining cache integrity across incremental
runs.

Rationale: Re-querying AI or music APIs for static track metadata or previously classified library
items consumes unnecessary API quota, increases execution time, and slows down library-wide automation.

### VIII. Grounded Metadata & Zero ISRC Hallucination
Generative AI models MUST NOT be prompted or expected to generate International Standard
Recording Codes (ISRCs) or opaque catalog identifiers; prompts and structured output schemas
MUST restrict track requests to verifiable human-readable attributes (artist and title). All track
resolution against Tidal or other streaming service APIs MUST rely exclusively on authoritative
catalog search or verified track metadata, never on synthetic codes. Any ISRC stored or processed
within the application MUST originate directly from authoritative provider APIs or authenticated
library tracks.

Rationale: Large language models frequently hallucinate plausible-looking but non-existent or
mismatched 12-character ISRC codes. Demanding or accepting AI-generated ISRCs causes lookup
failures, degraded recommendation accuracy, wasted API quota, and non-deterministic behavior.
Enforcing strict grounding in verified catalog data preserves playlist integrity and eliminates
silent matching errors.

### IX. CLI Ergonomics & Friction Reduction
Command-line interfaces and interactive workflows MUST prioritize ergonomic design
to minimize user friction, cognitive load, and unnecessary typing. CLI commands MUST
provide short, memorable, industry-standard names alongside descriptive aliases where
beneficial (such as `radio` alongside `track-radio`). Commands MUST provide intelligent,
sensible defaults for optional arguments (such as destination playlist naming and standard
track counts) to enable zero-friction, single-command quick execution. Error messages and
validation prompts MUST be concise, actionable, and immediately guide the user toward the
correct syntax without requiring external documentation.

Rationale: CLI tools are most effective and delightful when common tasks can be invoked
spontaneously with minimal friction. Overly verbose or strictly rigid argument requirements
discourage casual daily usage and increase user errors.

### X. Critical Dependency Currency & Capability Discovery
Before initiating technical planning, architectural design, or feature implementation that
relies on external client libraries (specifically critical client libraries such as `tidalapi`),
contributors and automated agents MUST inspect the library's latest releases, changelogs,
and repository updates for newly available functionality, improved endpoints, or resolved
limitations. When upstream library releases provide native methods or cleaner abstractions that
support the desired feature, the project MUST evaluate upgrading the dependency and adopting the
native capability rather than implementing custom workarounds, low-level HTTP calls, or brittle
private-attribute overrides. If new or required functionality is identified and adopted from a
critical client library, the required dependency version specification file (e.g., `pyproject.toml`
and lockfile) MUST be updated immediately to enforce the minimum required library version.

Rationale: External service APIs and client libraries evolve continuously. Implementing bespoke
logic without first checking for existing or newly added upstream capabilities increases maintenance
burden, risks divergence from API standards, and wastes development effort on problems already
solved upstream. Enforcing explicit version constraints in the project's dependency definition
prevents deployment of stale environments, eliminates runtime missing-attribute failures, and ensures
deterministic behavior across development, testing, and production runs.

## Mission
To create a personalized music discovery tool that seamlessly integrates with a
user's Tidal library, leverages Last.fm's recommendation engine, and automates
the creation of new playlists to enrich the user's listening experience.

## Technical Standards & Workflow

**Technology Stack:**
- **Language**: Python 3.12+
- **Dependency Management**: `uv`
- **CLI Framework**: `click`
- **Configuration**: `.env` for secrets/config
- **Logging**: Python `logging` module (stdout + file)

**Quality Gates:**
- All features MUST include error handling suitable for unattended execution.
- Code MUST adhere to modular design principles to support the Extensibility
  principle.
- All dependencies MUST be managed via `uv`.
- **Critical Dependency Currency & Capability Check**: Before planning or implementing
  features that interact with external service client libraries (most notably `tidalapi`),
  contributors MUST verify whether an updated release exists and check upstream documentation/changelogs
  for newly added methods or bug fixes that can fulfill the requirements natively. If new
  functionality is discovered and adopted, the required version specification file (`pyproject.toml`)
  MUST be updated to reflect the minimum version requirement before or alongside implementation.
- **Caching & Persistence**: Commands and services operating on library-wide metadata,
  track genres, or external AI/API queries MUST implement structured persistent local
  caching (e.g., SQLite/database) with explicit mechanisms to re-evaluate missing or
  "Unknown" classifications.
- **Batch & Synchronization Idempotency**: Workflows performing full library scans or
  playlist updates (e.g., genre playlist sorting) MUST handle pagination, batching,
  and API rate limits gracefully, ensuring operations are idempotent and re-runnable
  without duplicating playlists or tracks.
- **Zero ISRC Hallucination**: AI prompts, schemas, and completion handlers MUST
  strictly comply with Principle VIII by prohibiting synthetic ISRC generation and
  requiring string-based catalog search for track resolution.
- **CLI Ergonomics & Sensible Defaults**: New commands and CLI modifications MUST
  prioritize user ergonomics. Commands SHOULD support concise primary names with aliasing
  for discoverability, provide intelligent defaults for optional parameters to avoid
  unnecessary mandatory flags, and ensure validation errors provide immediate syntax guidance.
- **Validation**: Behavior changes MUST include targeted automated checks covering
  the affected CLI flow, service behavior, or error handling. Pure documentation-only
  changes may satisfy this gate with linting or direct content validation.
- **Documentation**: Every feature MUST include end-user documentation updates in
  README and/or feature quickstart content when behaviors, flags, constraints,
  or failure modes are added or changed. Any modification or addition to CLI parameters,
  options, flags, or default values MUST be reflected in README.md.
- **Understandability**: Documentation MUST explain what changed, how to use it,
  expected outcomes, and failure handling in clear language with at least one
  concrete command example.
- **Evidence**: When requirements, defaults, API capabilities, or operational
  facts are unknown, contributors MUST record the uncertainty and resolve it from
  the best available authoritative source before merge rather than inventing an
  answer.

## Governance
This Constitution supersedes all other practices.

Amendment Procedure:
- Proposed constitutional changes MUST include rationale, impacted templates, and
  migration notes where applicable.
- Amendments MUST be approved through project review before merge.
- Ratification date is immutable after first adoption; last amended date MUST be
  updated on every approved change.

Versioning Policy:
- MAJOR: Backward-incompatible governance changes or principle removals/redefinitions.
- MINOR: New principles/sections or materially expanded mandatory guidance.
- PATCH: Clarifications, wording improvements, and typo fixes with no governance
  behavior change.

Compliance Review Expectations:
- All PRs and reviews MUST verify compliance with Core Principles and Quality
  Gates.
- Reviewers MUST reject feature changes that lack documentation updates, skip
  required targeted validation, fail understandability checks, introduce awkward or
  excessively verbose CLI requirements when concise ergonomics and sensible defaults
  could be provided, invent unknown facts without authoritative verification,
  overlook available upstream functionality in critical client libraries like `tidalapi`
  when planning new integrations, fail to update required dependency version files
  (`pyproject.toml`) when upstream capabilities are adopted, or prompt/rely on AI-generated
  ISRC codes.

**Version**: 1.11.0 | **Ratified**: 2026-01-15 | **Last Amended**: 2026-09-14
