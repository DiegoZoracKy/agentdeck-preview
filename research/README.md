# AgentDeck Research Logs

**Complete experiment narratives from conception to insights.**

This directory contains the full story of each research experiment conducted with AgentDeck - from initial planning through execution to final analysis. Each experiment follows a structured workflow that documents the researcher's journey and serves as living documentation for future users.

---

## 📖 Purpose

Research logs serve multiple purposes:

1. **Reproducibility**: Complete record of what was done and why
2. **Transparency**: Document decisions, friction points, and learnings
3. **User Documentation**: Real examples of using AgentDeck for research
4. **Knowledge Transfer**: Help new researchers understand best practices
5. **Product Feedback**: Identify gaps and improvement opportunities in AgentDeck

---

## 🗂️ Structure

Each experiment gets its own dated folder with staged documentation:

```
research/
└── YYYY-MM-DD-{experiment-name}/
    ├── README.md           # Summary + Table of Contents (Stage 5)
    ├── 01-discovery.md     # How: AgentDeck API exploration (Stage 2)
    ├── 02-execution.md     # Doing: Live execution log (Stage 3)
    └── 03-analysis.md      # Learning: Results and insights (Stage 4)
```

**Stage 1 (Planning)** lives in `docs/planning/{EXPERIMENT-NAME}.md` and gets linked from the experiment README.

---

## 🔬 Experiment Workflow

### Stage 1: Planning (What & Why)
**Location**: `docs/planning/`

- Research question and hypothesis
- Experiment design (players, games, sample size)
- Success criteria and budget
- Value proposition

**Output**: Planning document (e.g., `OPENAI-STRATEGIC-BENCHMARKS.md`)

---

### Stage 2: Discovery (How)
**Location**: `research/{date}-{experiment}/01-discovery.md`

- What capabilities are needed?
- What does AgentDeck's API provide?
- Gaps and workarounds
- Implementation plan

**Output**: Discovery log documenting AgentDeck exploration

---

### Stage 3: Execution (Doing)
**Location**: `research/{date}-{experiment}/02-execution.md`

- Phase 0: Baseline validation (quality gates)
- Progressive execution log (live updates)
- Observations and adjustments
- Final results summary

**Output**: Execution log (updated in real-time as experiment runs)

---

### Stage 4: Analysis (Learning)
**Location**: `research/{date}-{experiment}/03-analysis.md`

- Statistical results (win rates, CIs, p-values, effect sizes)
- Visualizations and plots
- Key findings and surprises
- Implications for future work
- Limitations and caveats

**Output**: Analysis document with insights

---

### Stage 5: Archive (Posterity)
**Location**: `research/{date}-{experiment}/README.md`

- One-page summary of entire experiment
- Links to all stages
- Reproducibility information (seeds, commands, costs)
- Artifacts (recordings, plots, data)
- Next steps enabled by this experiment

**Output**: Experiment summary + move planning doc to archive

---

## 📚 Active Experiments

### OpenAI Strategic Benchmarks
- **Started**: 2025-11-08
- **Status**: 🔄 Stage 2 (Discovery Complete)
- **Research Question**: Compare strategic gameplay across OpenAI model configurations
- **Path**: [2025-11-08-openai-benchmarks/](2025-11-08-openai-benchmarks/)
- **Quick Links**:
  - [Planning](../planning/OPENAI-STRATEGIC-BENCHMARKS.md)
  - [Discovery](2025-11-08-openai-benchmarks/01-discovery.md)
  - [Execution](2025-11-08-openai-benchmarks/02-execution.md) (pending)
  - [Analysis](2025-11-08-openai-benchmarks/03-analysis.md) (pending)

---

## ✅ Completed Experiments

(None yet - this is our first!)

---

## 🎯 How to Use This as Documentation

**For Researchers Planning Experiments:**
1. Read an existing experiment's full narrative
2. Understand the workflow (Planning → Discovery → Execution → Analysis)
3. See how AgentDeck's API is used in practice
4. Learn from friction points and solutions

**For AgentDeck Contributors:**
1. Review discovery logs to find API gaps
2. Understand real user workflows
3. Identify feature requests backed by evidence
4. See which research utilities are actually used

**For New Team Members:**
1. Read completed experiments to understand research goals
2. See the spec-first discipline in action
3. Learn statistical best practices
4. Understand cost/performance tradeoffs

---

## 📋 Starting a New Experiment

1. **Create planning doc**: `docs/planning/YOUR-EXPERIMENT.md`
   - Research question, design, budget
   - Get team approval

2. **Create experiment folder**: `docs/research/YYYY-MM-DD-your-experiment/`
   - Copy template structure (see below)
   - Start with 01-discovery.md

3. **Execute and document**:
   - Update 02-execution.md live as you run experiments
   - Fill 03-analysis.md when complete
   - Create README.md summary

4. **Archive**:
   - Move planning doc to `docs/planning/archive/`
   - Update this index

---

## 🎨 Experiment Template

Use this template structure for new experiments:

```markdown
# 01-discovery.md Template

## 1. Charter Recap
Link to planning doc, summarize research question

## 2. Measurement Strategy
What metrics? Why? How will they answer the question?

## 3. AgentDeck Discovery
- Explore agentdeck.research.*
- Document what exists
- Identify gaps

## 4. Implementation Plan
How will you execute using AgentDeck's API?
```

```markdown
# 02-execution.md Template

## Phase 0: Quality Gates
Baseline validation results

## Execution Log
### YYYY-MM-DD HH:MM - Checkpoint 1
Results, observations, decisions

### YYYY-MM-DD HH:MM - Checkpoint 2
...
```

```markdown
# 03-analysis.md Template

## Statistical Results
Win rates, CIs, p-values, effect sizes

## Visualizations
Plots and charts

## Key Findings
What did we learn?

## Implications
What does this mean?

## Limitations
What should we be cautious about?
```

**Full template**: See [experiment-template/](experiment-template/) (TODO)

---

## 🔗 Related Documentation

- **[CONTRIBUTING.md](../../CONTRIBUTING.md)**: Spec-first workflow
- **[ROADMAP.md](../../ROADMAP.md)**: Current priorities and experiments
- **[docs/planning/](../planning/)**: Active and archived experiment plans
- **[experiments/](../../experiments/)**: Experiment code and data

---

## 📝 Lifecycle Management

**Active experiments**: Stay in root of research/
**Completed experiments**: Stay visible (don't archive - they're documentation!)
**Planning docs**: Move to `docs/planning/archive/` when experiment completes

**After 12+ months**: Evaluate if old experiments should be compressed/summarized, but generally keep them as they're valuable user documentation.

---

**Remember**: These logs are written for both **current team members** (reproducibility) and **future researchers** (documentation). Write for both audiences!

---

## ⚠️ Dependencies

**Statistical Analysis**:

The AgentDeck research utilities require `scipy` and `statsmodels` for statistical analysis (Wilson confidence intervals, binomial tests, effect sizes):

```bash
pip install scipy statsmodels
```

**If you forget**: Don't worry! AgentDeck records all match outcomes, so you can install dependencies and analyze post-hoc using existing session data (see [RESEARCHER-JOURNEY.md](2025-11-08-openai-benchmarks/RESEARCHER-JOURNEY.md) for example).

**What needs these packages**:
- `agentdeck.research.statistical.calculate_confidence_interval()`
- `agentdeck.research.statistical.statistical_significance()`
- `agentdeck.research.statistical.calculate_effect_size()`

**What doesn't**:
- Running experiments (matches execute fine)
- ProgressDisplay spectator (live telemetry works)
- Session recordings (always saved)
- Manual analysis (you can count wins yourself)

