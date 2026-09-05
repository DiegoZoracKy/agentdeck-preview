# AgentDeck Documentation

This directory contains the user-facing documentation that sits between the
root README and the component specifications.

## Start Here

- [Repository README](../README.md) - product overview, quick start, and flagship evidence
- [Research Arc](research-arc.md) - end-to-end architecture, genericity, extension requirements, deterministic/LLM boundaries, and user value
- [Reserve Courier walkthrough](../examples/reserve_courier/README.md) - local Game composition through Evidence and Finding, with an optional bounded model smoke
- [Execution hardening migration](e2e-hardening-migration.md) - single-player policies, partial Records, usage and CLI path changes
- [Specification Hub](../specs/SPEC.md) - source of truth for system contracts
- [Contributing Guide](../CONTRIBUTING.md) - development workflow, local setup, and review checklist
- [Viewer README](../viewer/README.md) - browser replay viewer usage
- [Security Policy](../SECURITY.md) - vulnerability reporting process
- [Release Checklist](release-checklist.md) - operational checklist for the next package release
- [Release Notes](releases/0.4.0.md) - version 0.4.0 changes, migration and validation

The docs are intentionally layered. Component-level behavior belongs in
`specs/`; Research remains downstream from the execution kernel while still
closing the public AgentDeck journey through Evidence and authored Findings.
The historical Agentic Edge workflow remains available at the
`agentic-edge-research` tag.
