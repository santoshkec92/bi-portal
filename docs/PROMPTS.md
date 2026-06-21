# Claude integration & prompt design

Implementation: `backend/app/services/claude_service.py`.

## 1. The thesis: chart shows *what*, Claude explains *why & what to do*

A static chart makes a stakeholder do the interpretation: read the bars, recall
the benchmark, spot the outlier, decide the action. The insight panel collapses
that into a grounded, executive-ready brief next to the chart — the same data,
pre-interpreted, with risks and next steps. That is the difference between a
dashboard people *look at* and one they *act on*, and it's what reduces the
"can you pull this for me?" tickets the brief is about.

## 2. Prompt structure (and why)

We use a three-part structure:

### (a) System prompt — persona + rules + output contract
Pins the model to a **named persona** (senior analyst for a specific function),
a **VP audience**, and hard rules:

- *"Ground every statement ONLY in the numbers provided. Never invent figures."*
  — the primary defense against hallucinated metrics.
- *"Be specific and quantitative; cite the actual numbers and deltas."* — forces
  the model to anchor to data, which also makes wrong outputs easy to catch.
- *"Lead with the single most decision-relevant takeaway."* — prioritizes signal.
- A **strict JSON output contract** with fixed keys
  (`headline`, `narrative`, `key_findings`, `risks`, `recommended_actions`).
  Structured output is renderable, testable, and bounds verbosity.

### (b) User prompt — structured data + light domain framing
We pass the **same JSON the chart renders from** (no separate "prose" view of
the data to drift from), plus short definitions (NRR, coverage ratio, slipped
deals) so the model reasons in the right vocabulary instead of guessing what a
field means.

### (c) Decode — defensive parse + degrade
We parse the JSON defensively (strip stray fences, locate the object, validate
required keys). On **any** failure we fall back to a deterministic,
data-derived insight so a dashboard never renders blank.

## 3. Why structured data in, structured JSON out

- **Determinism of shape**: the frontend always gets the same keys; the panel
  is a dumb renderer.
- **Grounding**: feeding the exact chart data (not a re-summarized version)
  removes a transcription gap where hallucinations creep in.
- **Evaluability**: we can assert on keys and even build regression checks
  ("headline cites a number present in the input").

## 4. Failure modes & how they're handled

| Failure mode | Handling |
|---|---|
| No API key configured | Deterministic mock insight (labeled `mock:no_api_key` in UI) |
| API timeout / 5xx | Bounded exponential-backoff retry (3 attempts), then mock |
| Malformed / non-JSON output | Defensive parse; if it fails → mock (`mock:error:*`) |
| Model invents a number | System-prompt grounding rule + data passed verbatim; reviewable because outputs cite specific figures |
| Runaway verbosity / cost | `max_tokens` cap + fixed JSON contract |
| Stale/contradictory narrative | Insight is generated from live data on each render; `generated_by` is surfaced for provenance |

The mock generator is **not a toy** — it reads the real metrics (NRR, coverage,
at-risk value) and composes a sensible, number-grounded narrative, so demos are
meaningful offline and the failure path is never embarrassing.

## 5. The two dashboards (why these two)

| Dashboard | Stakeholder | Decision it drives |
|---|---|---|
| **ARR Waterfall** | Finance / FP&A | Is net-new ARR healthy? Is churn or contraction the drag? Which segment to lean into? Feeds renewal forecasting. |
| **Pipeline Health** | Sales Ops | Is coverage ≥ 3x quota? What's stuck (90+ day aging) or slipping? Where to focus the quarter? |

They serve **different stakeholders** with **different mental models**
(retention bridge vs. funnel + aging), which is exactly where a tailored,
persona-aware insight beats a one-size chart.

## 6. Operationalizing at scale (beyond the prototype)

- **Cache** insights keyed by `(dashboard_type, data_hash, model)` — identical
  data shouldn't re-pay for tokens; warehouse data changes on a schedule.
- **Async pre-generation**: compute insights when dbt refreshes the marts, not
  on user click, so dashboards open instantly.
- **Evaluation harness**: a labeled set of (data → expected-finding) cases run in
  CI to catch prompt regressions when models or prompts change.
- **Guardrails**: numeric-consistency check (every figure in the output must
  appear in the input) and PII scan before display.
- **Cost controls**: per-tenant token budgets, model tiering (cheaper model for
  routine refreshes, Sonnet for ad-hoc deep dives).
