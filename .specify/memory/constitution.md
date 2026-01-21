<!--
Sync Impact Report:
- **Version Change**: 1.0.0 → 1.1.0
- **Modified Principles**:
  - Quality Gates: Added requirement for end-user documentation updates.
- **Added Sections**: None
- **Templates requiring updates**: 
  - .specify/templates/plan-template.md (⚠ pending - check "Constitution Check" section logic)
  - .specify/templates/spec-template.md (⚠ pending - might need explicit docs section)
- **Follow-up TODOs**: Review templates to ensure docs task is default.
-->
# Tidal Discovery Engine Constitution

## Core Principles

### I. User-Centricity
The project will prioritize a simple and intuitive command-line interface (CLI) that allows for easy configuration and operation. Configuration should be minimal and usage straightforward for end-users.

### II. Automation
The core value lies in automating the process of finding new music and creating playlists, saving the user time and effort. Workflows should be designed to run without manual intervention once configured (e.g., support for schedulers/cron).

### III. Personalization
By starting with the user's favorite tracks, the generated playlists will be tailored to their specific musical tastes. Algorithms and integrations must respect and leverage user data to maximize relevance.

### IV. Extensibility
The project will be built with a modular design to potentially accommodate other music services or recommendation engines in the future. Code should be loosely coupled and interfaces clearly defined.

### V. Reliability
The application will be robust, with proper error handling and logging to ensure consistent and predictable behavior, especially when running as a scheduled task. Failures should be handled gracefully and logged for diagnosis.

## Mission
To create a personalized music discovery tool that seamlessly integrates with a user's Tidal library, leverages Last.fm's recommendation engine, and automates the creation of new playlists to enrich the user's listening experience.

## Technical Standards & Workflow

**Technology Stack:**
- **Language**: Python
- **Dependency Management**: `uv`
- **CLI Framework**: `click`
- **Configuration**: `.env` for secrets/config
- **Logging**: Python `logging` module (stdout + file)

**Quality Gates:**
- All features must include error handling suitable for unattended execution.
- Code must adhere to modular design principles to support the Extensibility principle.
- All dependencies must be managed via `uv`.
- **Documentation**: End-user documentation (README, Quickstart) MUST be updated immediately when new features are added or existing behaviors change.

## Governance
This Constitution supersedes all other practices. Amendments require documentation, approval, and a corresponding version bump. All PRs and reviews must verify compliance with the Core Principles, particularly Reliability and Extensibility for new features.

**Version**: 1.1.0 | **Ratified**: 2026-01-15 | **Last Amended**: 2026-01-21
