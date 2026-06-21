"""Deterministic synthetic warehouse data.

Stands in for the Snowflake `ANALYTICS` schema so the portal is fully demoable
offline. Numbers are seeded (reproducible) and shaped to look like the output
of dbt models fed by Fivetran from Salesforce / NetSuite / the quoting system.

The shapes returned here intentionally match what the real Snowflake queries in
`snowflake_service.py` would return, so swapping the data source is transparent
to the dashboard endpoints.
"""
from __future__ import annotations

import random
from datetime import date, timedelta


def _rng(seed_key: str) -> random.Random:
    return random.Random(hash(("bi-portal", seed_key)) & 0xFFFFFFFF)


# --------------------------------------------------------------------------- #
# Finance: ARR Waterfall
# --------------------------------------------------------------------------- #
def arr_waterfall(period: str = "FY26-Q1", segment: str | None = None) -> dict:
    """Bridge from beginning to ending ARR for a period.

    Returns the canonical ARR bridge components plus a per-segment breakdown.
    """
    r = _rng(f"arr-{period}-{segment}")
    beginning = 42_000_000 + r.randint(-1_500_000, 1_500_000)

    new = r.randint(2_800_000, 4_200_000)
    expansion = r.randint(1_900_000, 3_100_000)
    contraction = -r.randint(500_000, 1_100_000)
    churn = -r.randint(900_000, 1_800_000)
    ending = beginning + new + expansion + contraction + churn

    segments = ["Enterprise", "Mid-Market", "SMB"]
    seg_weights = {"Enterprise": 0.55, "Mid-Market": 0.30, "SMB": 0.15}
    by_segment = []
    for seg in segments:
        w = seg_weights[seg]
        by_segment.append(
            {
                "segment": seg,
                "new": round(new * w),
                "expansion": round(expansion * w),
                "contraction": round(contraction * w),
                "churn": round(churn * w),
            }
        )

    gross_new = new + expansion
    gross_churn = abs(contraction) + abs(churn)
    nrr = round((beginning + expansion + contraction + churn) / beginning * 100, 1)
    grr = round((beginning + contraction + churn) / beginning * 100, 1)

    return {
        "period": period,
        "segment": segment or "All",
        "currency": "USD",
        "bridge": [
            {"label": "Beginning ARR", "value": beginning, "kind": "total"},
            {"label": "New", "value": new, "kind": "increase"},
            {"label": "Expansion", "value": expansion, "kind": "increase"},
            {"label": "Contraction", "value": contraction, "kind": "decrease"},
            {"label": "Churn", "value": churn, "kind": "decrease"},
            {"label": "Ending ARR", "value": ending, "kind": "total"},
        ],
        "by_segment": by_segment,
        "metrics": {
            "beginning_arr": beginning,
            "ending_arr": ending,
            "net_new_arr": ending - beginning,
            "gross_new_arr": gross_new,
            "gross_churn_arr": gross_churn,
            "nrr_pct": nrr,
            "grr_pct": grr,
        },
    }


# --------------------------------------------------------------------------- #
# Sales Ops: Pipeline Health
# --------------------------------------------------------------------------- #
_STAGES = [
    ("Qualification", 0.95),
    ("Discovery", 0.70),
    ("Proposal", 0.48),
    ("Negotiation", 0.32),
    ("Commit", 0.80),
]


def pipeline_health(quarter: str = "FY26-Q2", team: str | None = None) -> dict:
    r = _rng(f"pipe-{quarter}-{team}")
    quota = 12_000_000 + r.randint(-800_000, 800_000)

    funnel = []
    open_pipeline = 0
    for stage, win_rate in _STAGES:
        deals = r.randint(18, 60)
        value = deals * r.randint(45_000, 120_000)
        open_pipeline += value
        funnel.append(
            {
                "stage": stage,
                "deals": deals,
                "value": value,
                "win_rate_pct": round(win_rate * 100, 1),
                "avg_age_days": r.randint(12, 75),
            }
        )

    weighted_pipeline = sum(
        s["value"] * s["win_rate_pct"] / 100 for s in funnel
    )
    coverage = round(open_pipeline / quota, 2)

    # Aging buckets highlight stuck deals (a key Sales Ops signal).
    aging = [
        {"bucket": "0-30 days", "deals": r.randint(40, 70), "value": r.randint(3_000_000, 5_000_000)},
        {"bucket": "31-60 days", "deals": r.randint(25, 45), "value": r.randint(2_000_000, 4_000_000)},
        {"bucket": "61-90 days", "deals": r.randint(12, 25), "value": r.randint(1_000_000, 2_500_000)},
        {"bucket": "90+ days (at risk)", "deals": r.randint(8, 20), "value": r.randint(800_000, 2_000_000)},
    ]

    # Slipped deals: pushed from prior quarter close date.
    slipped_value = r.randint(900_000, 2_200_000)
    slipped_count = r.randint(6, 18)

    return {
        "quarter": quarter,
        "team": team or "All Teams",
        "currency": "USD",
        "funnel": funnel,
        "aging": aging,
        "metrics": {
            "quota": quota,
            "open_pipeline": open_pipeline,
            "weighted_pipeline": round(weighted_pipeline),
            "coverage_ratio": coverage,
            "slipped_value": slipped_value,
            "slipped_count": slipped_count,
            "at_risk_value": aging[-1]["value"],
        },
    }
