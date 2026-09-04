# Migrating to the hardened execution candidate

The execution candidate closes failures observed while using an installed package
from Game construction through Research. Source publication and PyPI release are
separate steps.

- **Single-player Games:** override `on_action_parse_failure` and choose an
  explicit policy, usually `ParseFailurePolicy.ABORT_MATCH`. The inherited
  FORFEIT policy requires an opponent. The Console rejects this composition
  before acquiring responses. Hidden Signal and Reserve Courier declare ABORT.
- **Batch errors:** ABORT now stops both serial and parallel batches with the
  original `MatchAbortedError`. Unexpected worker exceptions also propagate
  without a second scheduler wrapper. Already started work drains and keeps its
  Records and costs; pending work is cancelled best-effort. Handle partial
  Assembly/Study receipts rather than interpreting an exception as “nothing ran.”
- **Execution-error Records:** a started Match retains its observed events and
  last observed state, with `outcome: execution_error`, no invented winner, and
  the exception type/message. A response can exist in durable custody before a
  gameplay transition succeeds. Record cost totals and journal-only response
  counts are reconciled independently to avoid counting paid money twice.
- **Usage:** Assembly/Study `cost_usd` is a known-cost subtotal. When a Record's
  total cost is unavailable, its `known_cost_usd` still contributes. Player
  totals accumulate across workers and batches. Unknown charges remain unknown.
- **Provider retries:** OpenAI, Anthropic and Google SDK transport retries are
  disabled. `LLMPlayer.max_retries` owns the retry budget, as SPEC-LLM RE1 and
  provider-call custody PC2/PC7 already require. Each HTTP attempt now has its
  own custody entry; `max_retries=0` permits one attempt even on HTTP 503.
- **CLI JSON:** stdout contains one envelope; preparation and Monitor output
  goes to stderr. Resolve artifact paths relative to `data.output_root`.
  `receipt_path`, `finding_path` and `report_path` are now relative; the explicit
  host `output_root` remains absolute. Human-readable CLI output is unchanged.
- **RenderResult:** metadata is a detached, immutable JSON snapshot, including
  nested containers. Construct a new RenderResult to change it. `None` remains
  accepted as empty metadata. Ordinary reads, JSON and deepcopy remain supported.
- **Study loading:** an incomplete receipt can contain the ordered prefix of
  attempted groups. “Complete” requires all selected groups. Duplicate,
  reordered and skipped groups remain invalid.

The [Reserve Courier walkthrough](../examples/reserve_courier/README.md) provides
the smallest path and the complete installed-package Research journey.

Hidden Signal's explicit policy changes its Game implementation identity.
`research/references/hidden-signal/probe-v3.yaml` is a new derived acceptance
manifest for fresh execution. The revision-2 probe, canonical Record, Match
Surface and historical Study sources remain intact. The frozen Stage still
illustrates revision 2; new revision-3 runs produce their own external Stage.

See the [historical artifact provenance notes](../research/PROVENANCE.md) and
[release checklist](release-checklist.md) for artifact handling and package release.
