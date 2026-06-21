# What else would I build? (Task 5)

The prototype nails the governed shell + RBAC + Claude dashboards. Here is what
I'd layer on next, ordered by stakeholder value. For each: the capability, the
design, the trade-offs, and the open questions.

---

## 1. Conversational "ask-your-data" with a governed semantic layer ⭐

**Capability.** Let a stakeholder type *"What drove SMB churn last quarter?"* and
get a chart + answer — the real ticket-deflection win the brief describes.

**Design.** Claude does **NL → structured query against a semantic layer**, not
free-text SQL over raw tables. A YAML/dbt-metrics semantic layer defines
governed metrics (ARR, NRR, coverage) and dimensions; Claude emits a constrained
query object (metric + filters + grouping) that the backend compiles to
parameterized SQL. The query inherits the caller's RBAC + Snowflake row-access
policies, so you cannot ask your way past a permission boundary.

**Trade-offs.** Semantic layer is upfront effort but the only safe way to let an
LLM near a warehouse. Constrained query objects (vs. raw SQL) trade flexibility
for safety + cacheability — the right trade for self-serve.

**Open questions.** How much ad-hoc joining to allow? How to disambiguate
("revenue" = ARR or billings?) — probably a clarifying-question turn.

---

## 2. Scheduled refresh, snapshots & alerting

**Capability.** Dashboards refresh on the dbt cadence; insights are
pre-generated; users get a Slack/email digest ("Coverage dropped to 2.4x") and a
**Subscribe** button.

**Design.** A worker (Celery/Arq + Redis, or Snowflake Tasks) runs after the
mart refresh, recomputes data + Claude insight, writes an immutable **snapshot**
(so a published report is reproducible at a point in time), and evaluates alert
rules. This also removes Claude latency from the request path (see PROMPTS §6).

**Trade-offs.** Snapshots add storage + a freshness-vs-cost dial. Alert fatigue
is the real risk → thresholds must be per-metric and tunable.

**Open questions.** Point-in-time semantics when the underlying mart is
restated.

---

## 3. Lineage, freshness & trust signals

**Capability.** Every dashboard shows **"as of" freshness**, the dbt models /
source systems it derives from, and a trust badge. Finance won't forecast off a
number they can't trace.

**Design.** Ingest dbt `manifest.json` + source freshness; join lineage to each
report's metrics; surface a "Data lineage" drawer. Stale-source → warning banner.

**Trade-offs.** Couples the portal to dbt artifacts (acceptable — that's the
stack). Lineage granularity (model vs. column) is a depth/effort dial.

---

## 4. Full audit, access reviews & SOC2-friendly governance

**Capability.** Turn the existing `AuditEvent` log into an admin console:
who-saw-what, denied-access trends, periodic **access reviews** (approver
re-certifies their domain's members), and exportable evidence.

**Design.** Ship audit events to the warehouse/SIEM; build an admin dashboard
(reusing the portal!). Quarterly access-review workflow with attestations.

**Trade-offs.** Mostly product surface over data we already capture; the cost is
retention policy + PII handling on the log.

---

## 5. Hardened sessions & enterprise auth niceties

**Capability.** Server-side session revocation, "log out everywhere", SCIM
deprovisioning, step-up auth for sensitive Finance dashboards.

**Design.** Move from pure signed-cookie to a **Redis-backed session id**
(cookie holds an opaque id) so sessions are revocable; honor Okta SCIM for
instant deprovisioning; require a fresh `acr`/MFA claim for flagged reports.

**Trade-offs.** Reintroduces a (small) stateful dependency — justified once the
portal holds sensitive data. Until then, short-lived signed cookies are simpler.

---

## 6. Self-serve dashboard templates & a plugin model

**Capability.** Today there are two dashboard types in code. Let teams
instantiate **parameterized templates** (and eventually register new ones)
without a deploy — true self-serve.

**Design.** A dashboard-type registry (schema for config + data fetcher + chart
spec + prompt template). New types are config + a small module; advanced users
get a sandboxed, reviewed plugin path. Publishing workflow already governs
rollout.

**Trade-offs.** A plugin model is powerful but a security surface — sandboxing
and the existing review gate are mandatory.

---

### If I could build only one next: **#1 (conversational semantic layer)**.
It's the highest-leverage ticket-deflector and the most natural extension of the
Claude + RBAC + Snowflake foundation already in place — and the semantic layer it
requires is the same investment that makes #2 and #3 safe.
