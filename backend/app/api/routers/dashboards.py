"""Dashboard rendering: data (Snowflake/synthetic) + Claude insight panel.

A dashboard render is the join of three things:
  1. structured data from the warehouse (via snowflake_service)
  2. a visual layer (the frontend turns `data` into charts/tables)
  3. a Claude-generated natural-language insight grounded in that same data

RBAC is enforced before any data is fetched: you can only render a report you
are entitled to view, so domain isolation holds even with a direct URL.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_principal, get_current_user
from ...auth.rbac import Domain, Principal
from ...models import DashboardType, Report, User
from ...database import get_db
from ...schemas import DashboardOut, InsightOut
from ...services import authz
from ...services.claude_service import claude_service
from ...services.provisioning import audit
from ...services.snowflake_service import snowflake_service

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

_TITLES = {
    DashboardType.ARR_WATERFALL: "ARR Waterfall",
    DashboardType.PIPELINE_HEALTH: "Pipeline Health",
}


def _render(dashboard_type: DashboardType, config: dict) -> tuple[dict, dict, str, str]:
    if dashboard_type == DashboardType.ARR_WATERFALL:
        data = snowflake_service.arr_waterfall(
            period=config.get("period", "FY26-Q1"),
            segment=config.get("segment"),
        )
        key = "arr_waterfall"
    elif dashboard_type == DashboardType.PIPELINE_HEALTH:
        data = snowflake_service.pipeline_health(
            quarter=config.get("quarter", "FY26-Q2"),
            team=config.get("team"),
        )
        key = "pipeline_health"
    else:
        raise HTTPException(400, "Unsupported dashboard type")

    insight = claude_service.generate_insight(key, data)
    return data, insight, snowflake_service.backend, claude_service.backend


@router.get("/{report_id}", response_model=DashboardOut)
def render_report_dashboard(
    report_id: int,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOut:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Not found")
    # Enforce *before* fetching any analytical data.
    if not authz.can_view_report(principal, user, report):
        audit(db, user_email=user.email, action="render_dashboard", allowed=False,
              resource_type="report", resource_id=report_id)
        raise HTTPException(404, "Not found")

    data, insight, data_backend, insight_backend = _render(
        report.dashboard_type, report.config or {}
    )
    audit(db, user_email=user.email, action="render_dashboard", resource_type="report",
          resource_id=report_id)
    return DashboardOut(
        dashboard_type=report.dashboard_type.value,
        title=report.title or _TITLES[report.dashboard_type],
        data=data,
        insight=InsightOut(**insight),
        data_backend=data_backend,
        insight_backend=insight_backend,
    )


@router.post("/preview", response_model=DashboardOut)
def preview_dashboard(
    body: dict,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
) -> DashboardOut:
    """Render a dashboard from ad-hoc params while drafting (not persisted).

    Restricted to authors of the chosen target domain so previews respect the
    same domain boundary as published reports.
    """
    try:
        dashboard_type = DashboardType(body.get("dashboard_type"))
    except ValueError:
        raise HTTPException(422, "Invalid dashboard_type")
    target = body.get("target_domain")
    if target:
        try:
            domain = Domain(target)
        except ValueError:
            raise HTTPException(422, "Invalid target_domain")
        if not principal.can_author_in(domain):
            raise HTTPException(403, f"You are not a member of {domain.label}")

    config = body.get("config", {})
    data, insight, data_backend, insight_backend = _render(dashboard_type, config)
    return DashboardOut(
        dashboard_type=dashboard_type.value,
        title=_TITLES[dashboard_type],
        data=data,
        insight=InsightOut(**insight),
        data_backend=data_backend,
        insight_backend=insight_backend,
    )
