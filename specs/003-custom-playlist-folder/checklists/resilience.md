# Checklist: Resilience & Error Handling for Custom Playlists

**Purpose**: Validate robustness requirements, specifically regarding API failures and recovery.
**Created**: 2026-01-15
**Feature**: [Custom Tidal Playlist Folders](../spec.md)

## Retry Logic
- [x] Is the "exponential backoff" algorithm defined (e.g., base delay, max delay)? [Clarity, Spec §FR-5]
- [x] Are "transient network errors" clearly defined (e.g., specific HTTP status codes like 503, 504)? [Clarity, Spec §FR-5]
- [x] Is the maximum retry count (3) explicitly stated as a hard requirement? [Completeness, Spec §FR-5]

## Fallback Behavior
- [x] Is the "root level" fallback behavior mandatory for *all* folder creation/placement failures? [Coverage, Spec §FR-5]
- [x] Are there any exceptions where the process should abort instead of falling back (e.g., auth failure)? [Edge Case, Gap]

## User Feedback (Warnings)
- [x] Is the specific content/format of the warning log defined? [Clarity, Spec §FR-5]
- [x] Is the "non-blocking" nature of the warning explicitly required? [Completeness, Spec §FR-5]
- [x] Is the output stream (stderr vs stdout) for warnings clearly specified? [Clarity, Spec §FR-5]

## State Preservation
- [x] Is the requirement to preserve the empty folder explicitly defined for the "placement failure" scenario? [Consistency, Spec §FR-5]
- [x] Does the spec address cleanup of partial state if the *root* fallback also fails? [Edge Case, Gap]
