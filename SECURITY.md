# Security Policy

AgentDeck is research infrastructure for running and analyzing AI-agent
experiments. Please report vulnerabilities privately before opening a public
issue.

## Reporting

Send reports to the project maintainer through GitHub:

- Open a private security advisory on GitHub when available.
- If that is not available, contact the maintainer account listed on the
  repository and include enough detail to reproduce the issue.

Please include:

- affected version or commit
- operating system and Python version
- reproduction steps
- expected vs. actual behavior
- any relevant logs, stack traces, or proof-of-concept files

## Scope

Security-sensitive issues include:

- arbitrary code execution through records, viewers, package manifests, or
  research scripts
- path traversal or unsafe file writes during export, validation, replay, or
  packaging
- accidental exposure of provider credentials or environment variables
- unsafe handling of untrusted replay JSON or metadata sidecars

Model behavior, prompt quality, benchmark conclusions, and ordinary research
limitations should be filed as regular issues instead.

## Supported Versions

The latest release and the current `main` branch receive security fixes.

## Disclosure

Please allow reasonable time for triage and patching before public disclosure.
