# Checklist: Gemini SDK Migration Requirements Quality

**Purpose**: Validation of requirements quality, completeness, and rigor for the migration to `google-genai` SDK.
**Focus**: Technical Correctness, Error Handling, Formal Quality Gate.
**Created**: 2026-02-02

## 1. Technical Correctness & SDK Specifics
- [ ] CHK001 - Are the installation requirements for `google-genai` (vs `google-generativeai`) explicitly documented? [Completeness, Plan Phase 1]
- [ ] CHK002 - Is the instantiation pattern for `genai.Client` (vs `genai.configure`) clearly specified? [Clarity, Research]
- [ ] CHK003 - Are the import statement requirements (`from google import genai`) unambiguous? [Clarity, Plan Phase 2]
- [ ] CHK004 - Is the syntax for `client.models.generate_content` call structure explicitly defined? [Clarity, Research]
- [ ] CHK005 - Are the requirements for Pydantic model (`Song`) integration vs raw JSON schema options clearly decided? [Consistency, Research]
- [ ] CHK006 - Is the mechanism for passing `GEMINI_API_KEY` (client arg vs implicit env var) explicitly defined? [Clarity, Plan]

## 2. Error Handling & Resilience
- [ ] CHK007 - Is the mapping between specific `genai.errors` and user-facing messages defined? [Completeness, Gap]
- [ ] CHK008 - Are requirements defined for handling `ClientError` (e.g. invalid arguments) specifically? [Coverage, Edge Case]
- [ ] CHK009 - Are requirements defined for handling `ServerError` or `ServiceUnavailable` from the new SDK? [Coverage, Recovery]
- [ ] CHK010 - Is the behavior specified for Quota/Rate Limit exceptions? [Coverage, Non-Functional]
- [ ] CHK011 - Are requirements specified for handling malformed/partial responses from the new `Parsed` object? [Completeness, Edge Case]

## 3. Implementation Quality Gates
- [ ] CHK012 - Are pre-call validation checks (e.g. API key presence) consistent with the new SDK's behavior? [Consistency]
- [ ] CHK013 - Is the fallback behavior defined if the `google.genai` library import fails? [Edge Case, Gap]
- [ ] CHK014 - Are the response constraints (e.g., MIME type `application/json`) defined utilizing the new `GenerateContentConfig` type? [Clarity]
- [ ] CHK015 - Does the plan explicitly exclude or include async/await usage requirements? [Ambiguity]

## 4. Functional Parity
- [ ] CHK016 - Are requirements defined for maintaining the `shuffle` (Deep Cuts) prompt logic within the new `contents` parameter? [Consistency, Spec]
- [ ] CHK017 - Is the output format (list of `Song` objects) guaranteed to match the original service interface? [Consistency, Contract]
- [ ] CHK018 - Are existing logging requirements maintained or updated for the new Client structure? [Completeness]
