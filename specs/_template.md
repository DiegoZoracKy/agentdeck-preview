# SPEC-{COMPONENT}: {Title}

> Status: Template
> Version: 0.1.0
> Last Updated: YYYY-MM-DD
> Implementation: ⬜ Not Started
> Review State: {draft|consensus-approved}
> Audience: {Primary readers (callers, game authors, contributors, etc.)}

## 1. Purpose
- Who relies on this component (callers, game authors, contributors)?
- What user problem does it solve?
- Why does it exist within AgentDeck’s architecture?

## 2. Scope & Philosophy Alignment
- Reference relevant principles from `SPEC.md` and `AGENTS.md`.
- Note any guiding philosophies (Simplicity, Separation, Composition, Reproducibility).

## 3. Responsibilities
- Enumerate the single responsibility (per Unix rule) for this component.
- Detail key sub-responsibilities in concise bullets, written for the primary user (caller, contributor, etc.).

## 4. Data Structures (optional)
- Capture canonical data contracts (context objects, results, payload schemas).
- Prefer dataclass-style snippets or concise bullet descriptions.
- Highlight which fields are required vs optional and how they tie to other specs.

## 5. Public API
- List external entry points with signatures followed by bullet-style parameter notes.
- Record preconditions/postconditions or defaults as short bullets (avoid duplicate prose).
- Note any read-only properties or lifecycle helpers alongside methods.

## 6. Invariants & Guarantees
- Bullet point explicit invariants the component MUST uphold.
- Include performance, determinism, and error-handling guarantees.

## 7. Data Flow & Interaction
- Summarise interactions in single-line arrow flows (e.g., `Init: Facade → Console → State`).
- Link to adjacent specs when referencing responsibilities. Add diagrams only if the flow cannot be captured concisely.

## 8. Error Handling & Edge Cases
- Document expected errors and fallback strategies.
- Clarify logging, retries, and failure modes.

## 9. Examples
- Provide 3 focused, runnable snippets showing canonical usage (happy path, common variant, replay/edge case as relevant).
- Avoid redundant snippets that repeat the same contract.

## 10. Testing Strategy
- Map test cases to invariants.
- Specify required integration vs unit test coverage.

## 11. Design Rationale
- Summarize only non-obvious decisions (e.g., "Always-present seed").
- Reference alternatives or historical context briefly; skip rationale already implied by the API.

## 12. Open Questions / Future Work
- List outstanding questions, TODOs, or experimental ideas.

## 13. References
- Link to related specs, README sections, migration guides, etc.
