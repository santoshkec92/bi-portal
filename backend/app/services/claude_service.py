"""Claude-powered insight generation.

Design philosophy
-----------------
The chart shows *what* happened; Claude explains *why it matters and what to do*.
We treat the LLM as a senior analyst writing an executive brief, not a chatbot.

Prompt structure (see docs/PROMPTS.md for the full rationale):
1. **System prompt** pins the persona, the audience, hard grounding rules
   ("use only the numbers provided; never invent figures"), and a strict output
   contract (JSON with fixed keys). This is the main lever against
   hallucination and rambling.
2. **User prompt** is fully structured: the same JSON the chart renders from,
   plus light domain framing (what NRR/coverage mean) so the model reasons in
   the right vocabulary.
3. We request a **typed JSON object** and parse it defensively; on any parse or
   API failure we degrade to a deterministic, data-derived narrative so a
   dashboard never renders blank.

Failure modes we explicitly handle: no API key (mock), API error/timeout
(retry then mock), malformed JSON (repair-or-mock). Costs/latency are bounded
by `claude_max_tokens` and by caching opportunities noted in FUTURE_WORK.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..config import settings

SYSTEM_PROMPT = """\
You are a senior analyst embedded in the AI Data Platform team of a B2B SaaS \
company. You write crisp, executive-ready insight for a named business function \
(Finance, Sales Ops, RevOps, Customer Success).

Rules you MUST follow:
- Ground every statement ONLY in the numbers provided in the user message. \
Never invent, estimate, or extrapolate figures that are not present.
- Be specific and quantitative: cite the actual numbers and deltas you are \
reasoning about.
- Prioritize signal: lead with the single most decision-relevant takeaway.
- Be honest about risk and uncertainty; do not editorialize or use hype.
- Audience is a VP/executive. No filler, no restating the question.

Return ONLY a valid JSON object with EXACTLY these keys:
{
  "headline": string,            // <= 90 chars, the one-line takeaway
  "narrative": string,           // 2-3 sentence executive summary
  "key_findings": [string],      // 2-4 bullet insights, each grounded in a number
  "risks": [string],             // 1-3 risks or watch-items
  "recommended_actions": [string]// 1-3 concrete next steps for this function
}
No prose outside the JSON. No markdown fences."""


def _arr_user_prompt(data: dict[str, Any]) -> str:
    m = data["metrics"]
    return (
        "Dashboard: ARR Waterfall for Finance.\n"
        f"Period: {data['period']} | Segment: {data['segment']} | "
        f"Currency: {data['currency']}\n\n"
        "Definitions: NRR = net revenue retention (expansion+contraction+churn "
        "vs beginning ARR); GRR = gross revenue retention (excludes expansion). "
        "Net New ARR = ending - beginning.\n\n"
        "Bridge components (USD):\n"
        f"{json.dumps(data['bridge'], indent=2)}\n\n"
        "Headline metrics:\n"
        f"{json.dumps(m, indent=2)}\n\n"
        "By segment:\n"
        f"{json.dumps(data['by_segment'], indent=2)}\n\n"
        "Write the insight brief for the Finance VP."
    )


def _pipeline_user_prompt(data: dict[str, Any]) -> str:
    m = data["metrics"]
    return (
        "Dashboard: Pipeline Health for Sales Ops.\n"
        f"Quarter: {data['quarter']} | Team: {data['team']} | "
        f"Currency: {data['currency']}\n\n"
        "Definitions: Coverage ratio = open pipeline / quota (3x is a common "
        "healthy benchmark). Weighted pipeline applies stage win-rates. "
        "Slipped deals pushed their close date out of the prior quarter.\n\n"
        "Funnel by stage:\n"
        f"{json.dumps(data['funnel'], indent=2)}\n\n"
        "Aging buckets:\n"
        f"{json.dumps(data['aging'], indent=2)}\n\n"
        "Headline metrics:\n"
        f"{json.dumps(m, indent=2)}\n\n"
        "Write the insight brief for the Sales Ops VP."
    )


_PROMPT_BUILDERS = {
    "arr_waterfall": _arr_user_prompt,
    "pipeline_health": _pipeline_user_prompt,
}


class ClaudeService:
    def __init__(self) -> None:
        self._configured = settings.claude_configured
        self._client = None
        if self._configured:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=settings.anthropic_api_key)

    @property
    def backend(self) -> str:
        return "claude" if self._configured else "mock"

    def generate_insight(self, dashboard_type: str, data: dict[str, Any]) -> dict:
        builder = _PROMPT_BUILDERS.get(dashboard_type)
        if builder is None:
            raise ValueError(f"No prompt builder for dashboard '{dashboard_type}'")
        user_prompt = builder(data)

        if not self._configured:
            return _mock_insight(dashboard_type, data, reason="no_api_key")

        try:
            raw = self._call_claude(user_prompt)
            insight = _parse_insight(raw)
            insight["generated_by"] = f"claude:{settings.claude_model}"
            return insight
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never 500
            fallback = _mock_insight(dashboard_type, data, reason=f"error:{type(exc).__name__}")
            return fallback

    def _call_claude(self, user_prompt: str, max_attempts: int = 3) -> str:  # pragma: no cover - needs key
        # Small exponential backoff; bounded so a dashboard never hangs.
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                resp = self._client.messages.create(
                    model=settings.claude_model,
                    max_tokens=settings.claude_max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return "".join(b.text for b in resp.content if b.type == "text")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_attempts - 1:
                    time.sleep(min(2**attempt, 8))
        raise last_exc  # type: ignore[misc]


def _parse_insight(raw: str) -> dict:
    """Defensive parse: strip stray fences, locate the JSON object."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in Claude response")
    obj = json.loads(text[start : end + 1])
    required = {"headline", "narrative", "key_findings", "risks", "recommended_actions"}
    if not required.issubset(obj):
        raise ValueError(f"Insight missing keys: {required - set(obj)}")
    return obj


# --------------------------------------------------------------------------- #
# Deterministic fallback ("mock") insight — grounded in the same numbers.
# --------------------------------------------------------------------------- #
def _fmt(n: float) -> str:
    return f"${n/1_000_000:.1f}M" if abs(n) >= 1_000_000 else f"${n:,.0f}"


def _mock_insight(dashboard_type: str, data: dict, reason: str) -> dict:
    if dashboard_type == "arr_waterfall":
        m = data["metrics"]
        net = m["net_new_arr"]
        direction = "grew" if net >= 0 else "contracted"
        top_seg = max(data["by_segment"], key=lambda s: s["new"] + s["expansion"])
        insight = {
            "headline": f"ARR {direction} {_fmt(abs(net))} to {_fmt(m['ending_arr'])} (NRR {m['nrr_pct']}%)",
            "narrative": (
                f"ARR moved from {_fmt(m['beginning_arr'])} to {_fmt(m['ending_arr'])} "
                f"in {data['period']}, a net change of {_fmt(net)}. Net revenue "
                f"retention is {m['nrr_pct']}% and gross retention {m['grr_pct']}%, "
                f"with {top_seg['segment']} driving the most gross new ARR."
            ),
            "key_findings": [
                f"Gross new ARR of {_fmt(m['gross_new_arr'])} (new + expansion).",
                f"Gross churn + contraction of {_fmt(m['gross_churn_arr'])} offset growth.",
                f"{top_seg['segment']} contributed {_fmt(top_seg['new'] + top_seg['expansion'])} in new+expansion.",
            ],
            "risks": [
                "NRR below 100% would signal the base is shrinking pre-new-business."
                if m["nrr_pct"] < 100
                else f"Churn of {_fmt(abs(m['gross_churn_arr']))} is the main drag to monitor.",
            ],
            "recommended_actions": [
                "Pressure-test the renewal forecast against the contraction trend.",
                f"Double down on {top_seg['segment']} expansion motions that are working.",
            ],
        }
    elif dashboard_type == "pipeline_health":
        m = data["metrics"]
        cov = m["coverage_ratio"]
        healthy = cov >= 3.0
        at_risk = m["at_risk_value"]
        insight = {
            "headline": f"Coverage {cov}x on {_fmt(m['quota'])} quota; {_fmt(at_risk)} aging 90+ days",
            "narrative": (
                f"{data['team']} enters {data['quarter']} with {_fmt(m['open_pipeline'])} "
                f"open pipeline against a {_fmt(m['quota'])} quota — a {cov}x coverage "
                f"ratio ({'healthy' if healthy else 'below the 3x benchmark'}). Weighted "
                f"pipeline is {_fmt(m['weighted_pipeline'])}."
            ),
            "key_findings": [
                f"{_fmt(at_risk)} sits in the 90+ day at-risk aging bucket.",
                f"{m['slipped_count']} deals worth {_fmt(m['slipped_value'])} slipped from last quarter.",
                f"Weighted pipeline of {_fmt(m['weighted_pipeline'])} vs {_fmt(m['quota'])} quota.",
            ],
            "risks": [
                "Coverage below 3x raises the risk of missing quota; build more pipeline."
                if not healthy
                else "Concentration in late stages could swing the forecast if deals slip.",
            ],
            "recommended_actions": [
                "Run a stuck-deal review on the 90+ day bucket this week.",
                "Re-confirm close dates on slipped deals before committing the forecast.",
            ],
        }
    else:
        insight = {
            "headline": "Insight unavailable",
            "narrative": "No insight generator configured for this dashboard.",
            "key_findings": [],
            "risks": [],
            "recommended_actions": [],
        }
    insight["generated_by"] = f"mock:{reason}"
    return insight


claude_service = ClaudeService()
