# SPEC-GAME-STAGE: Portable Browser Game Stage Contract

> Status: Final
> Version: 0.2.1
> Last Updated: 2026-08-09
> Implementation: Complete
> Review State: Consensus-approved
> Audience: Instrument authors, Builder authors, viewer hosts, Core maintainers

## 1. Purpose

Define a portable, Game-specific browser surface that turns a sanitized Match Surface
into an inspectable Game Stage without coupling AgentDeck to a frontend framework or
allowing presentation code to reinterpret canonical evidence.

## 2. Scope And Terminology

- A **Renderer** formats a Player-visible Game view for an AI Player's prompt.
- A **Match Surface** is the Core-produced, redacted replay protocol.
- A **Game Stage** is a human-facing static browser bundle that consumes a Match Surface.
- A **Host** owns timeline controls, containment, and delivery of Match Surface data.

A Stage MAY use HTML, CSS, DOM, Canvas, WebGL, Three.js, WASM, or bundled framework
code. AgentDeck specifies observable behavior and safety boundaries, not rendering
technology. A Stage MUST NOT affect gameplay, records, scoring, or research facts.

## 3. Package Declaration

Manifest schema `1.1` adds:

```yaml
presentation:
  redactor_entry_point: package.presentation:visible_state
  viewer: presentation/index.html
  viewer_protocol: agentdeck-stage/1.1
claims:
  requested: [runnable, presentable, stage_ready]
```

The entry file and every runtime dependency MUST be under `presentation/`. The bundle
is self-contained and MUST NOT require a CDN, provider credential, remote font, remote
image, analytics endpoint, websocket, or other network service.

`stage_ready` requires `runnable` and `presentable`. It is distinct from `presentable`:
a Game can always use the generic Match Surface without declaring a custom Stage.

## 4. Host Protocol

Messages are strict JSON-compatible objects sent with `window.postMessage`. Both sides
MUST use `protocol: "agentdeck-stage/1.1"`.

### 4.1 Stage To Host

```json
{"type":"agentdeck:stage-ready","protocol":"agentdeck-stage/1.1"}
{"type":"agentdeck:stage-loaded","protocol":"agentdeck-stage/1.1","match_id":"...","frame_count":6}
{"type":"agentdeck:stage-rendered","protocol":"agentdeck-stage/1.1","frame_index":0}
{"type":"agentdeck:stage-error","protocol":"agentdeck-stage/1.1","message":"..."}
```

The Stage emits `ready` only after its message listener and rendering runtime are
available. It emits `loaded` only after accepting and validating the supplied initial
context. It emits one `rendered` acknowledgement after each successful render command.

### 4.2 Host To Stage

```json
{"type":"agentdeck:stage-load","protocol":"agentdeck-stage/1.1","context":{"schema_version":"1.0","match":{"match_id":"...","game":"...","seed":42},"players":[{"name":"Alpha","model":null}],"frame_count":6}}
{"type":"agentdeck:stage-render","protocol":"agentdeck-stage/1.1","frame_index":0,"frame":{}}
```

The initial context contains exactly its schema version, minimal match identity
(`match_id`, `game`, and `seed`), certified pre-match Player identities (`name` and
`model`), and `frame_count`. `name` is a string. `model` is a string when the Player
declares a model and `null` otherwise; a Stage MUST handle either form without treating
a model-less deterministic fixture as invalid.
It MUST NOT contain gameplay frames, winner, conclusions, markers, economics, final
state, or other information produced after match start. For each render command, the
Host supplies only the exact currently authorized certified frame. The Stage MUST NOT
fetch a record, infer hidden or future state, or require a Game object. The Stage MAY
provide secondary controls over information already delivered, but Host commands remain
the sole authority that advances frame knowledge.

Protocol `1.0` was an unreleased authoring contract and is superseded rather than kept
as a `stage_ready` compatibility mode. Its full-surface load gave presentation code
knowledge of future frames and match results before the Host advanced playback.

## 5. Containment And Security

The Host loads the entry in a unique-origin iframe with exactly `sandbox="allow-scripts"`.
It does not grant same-origin access, forms, popups, top navigation, downloads, or
storage authority. Certification serves only contained `presentation/` files and denies
all external requests.

Certification applies a restrictive Content Security Policy with no connections,
objects, frames, forms, or external base URL. Inline styles/scripts and bundled WASM are
allowed so the contract remains framework-neutral. A caller executing untrusted Stage
code still owns process/container isolation under `SPEC-ARTIFACT-SAFETY`.

## 6. Browser Certification

The authoritative probe uses the certified Match Surface generated from the package's
deterministic fixture. It runs at least:

- desktop: `1280 x 720`;
- mobile: `390 x 844`.

For each viewport, it MUST:

1. load the sandboxed Stage with no external network request;
2. observe `ready` and send the exact minimal initial context without gameplay or result data;
3. observe `loaded` with the exact match ID and frame count;
4. render every gameplay frame in order and observe an exact acknowledgement for each;
5. capture every rendered frame in memory and find nonblank visual output for each;
6. retain the first and last screenshots and, when their indices differ, find a
   detectable visual change between those boundary frames;
7. find no page error, error-level console message, protocol error, or document overflow.

Screenshots are diagnostic certification artifacts. Pixel bytes and browser versions
are not canonical report inputs; pass/fail behavior and artifact names are.

If the optional browser-certification dependency is unavailable, `stage_ready`
certification MUST fail with an actionable message and MUST NOT silently downgrade to
file containment.

## 7. Invariants

1. **STG1 Distinct Presentation Role**: A Game Stage consumes presentation data for humans and MUST NOT replace the Player Renderer, mutate gameplay, score behavior, or author research facts.
2. **STG2 Technology-Neutral Bundle**: The contract MUST NOT require a frontend framework or drawing technology; any bundled implementation is valid when it satisfies the protocol and certification behavior.
3. **STG3 Temporally Bounded Presentation Input**: The Host MUST initially supply only minimal certified match context and MUST subsequently supply only the currently authorized certified frame; a Stage MUST NOT receive the complete Match Surface, future frames, result data, canonical records, Game objects, provider access, or hidden state.
4. **STG4 Contained Offline Runtime**: Every Stage dependency MUST resolve under `presentation/`, and browser certification MUST reject external network attempts or escaping paths.
5. **STG5 Sandboxed Host Boundary**: The Host MUST run Stage code in a unique-origin iframe with scripts as its only sandbox capability.
6. **STG6 Exact And Diagnosable Host Protocol**: Ready, load, loaded, render, rendered, and error messages MUST use the declared protocol and exact match/frame identities; browser certification MUST receive an exact render acknowledgement for every fixture gameplay frame and MUST surface a valid Stage error immediately while waiting for loaded or rendered state.
7. **STG7 Responsive Runtime Health**: Desktop and mobile probes MUST complete without page errors, error-level console messages, protocol errors, or document overflow.
8. **STG8 Visible Frame Projection**: Every fixture gameplay frame MUST produce nonblank visual output and an exact render acknowledgement; when first and last indices differ, their output MUST be detectably different without requiring consecutive frames to differ.

## 8. Failure Handling

- Missing entry, protocol, prerequisite tier, or contained asset fails declarative validation.
- Future-data access, timeout, wrong acknowledgement, blank output, overflow, console/page error, or network
  attempt fails `stage_ready` without removing independently awarded lower tiers.
- A failed Stage probe MUST NOT overwrite a prior successful certification report.

## 9. Testing Strategy

- A tiny external Stage proves framework-neutral postMessage integration.
- Adversarial bundles cover external fetch, wrong protocol, future-data access, a blank
  intermediate frame, missing render acknowledgement, console error, and mobile overflow.
- The Builder acceptance test generates a novel Game and Stage from informal intent,
  then uses the same Core browser certifier used by hand-authored packages.

## 10. Rationale

The Stage protocol is deliberately smaller than a viewer framework. Match Surface owns
facts, the Host owns playback, and the Stage owns expression. This lets an AI author a
distinctive visual world while the laboratory retains replay parity, visibility, and
safe embedding.

## 11. References

- [SPEC-INSTRUMENT-PACKAGE.md](SPEC-INSTRUMENT-PACKAGE.md)
- [SPEC-MATCH-SURFACE-PROJECTION.md](SPEC-MATCH-SURFACE-PROJECTION.md)
- [SPEC-ARTIFACT-SAFETY.md](SPEC-ARTIFACT-SAFETY.md)
- [SPEC-RENDERER.md](SPEC-RENDERER.md)
