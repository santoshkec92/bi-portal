"""Reports = dashboards, plus the governed publishing workflow.

Lifecycle:
    DRAFT ──submit──> IN_REVIEW ──approve──> PUBLISHED (moved to domain folder)
       ^                  │
       └──changes────────┘ (reject -> CHANGES_REQUESTED, back to the author)

Authorization is enforced via `services.authz` at every transition.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_principal, get_current_user
from ...auth.rbac import Domain, Principal
from ...database import get_db
from ...models import (
    ApprovalDecision,
    ApprovalRequest,
    Folder,
    FolderType,
    Report,
    ReportStatus,
    User,
)
from ...schemas import (
    ApprovalDecisionIn,
    ApprovalQueueItem,
    PublishRequest,
    ReportCreate,
    ReportOut,
    ReportUpdate,
)
from ...services import authz
from ...services.provisioning import audit

router = APIRouter(prefix="/api/reports", tags=["reports"])


def serialize(report: Report) -> ReportOut:
    return ReportOut(
        id=report.id,
        title=report.title,
        description=report.description,
        dashboard_type=report.dashboard_type,
        status=report.status,
        folder_id=report.folder_id,
        owner_email=report.owner.email,
        target_domain=report.target_domain,
        config=report.config or {},
        created_at=report.created_at,
        updated_at=report.updated_at,
        published_at=report.published_at,
    )


def _personal_folder(db: Session, user: User) -> Folder:
    folder = (
        db.query(Folder)
        .filter(Folder.type == FolderType.PERSONAL, Folder.owner_user_id == user.id)
        .first()
    )
    if folder is None:
        raise HTTPException(500, "Personal workspace missing")
    return folder


def _domain_folder(db: Session, domain: Domain) -> Folder:
    folder = (
        db.query(Folder)
        .filter(Folder.type == FolderType.DOMAIN, Folder.domain == domain.value)
        .first()
    )
    if folder is None:
        raise HTTPException(500, f"Domain folder for {domain.value} missing")
    return folder


@router.get("/mine", response_model=list[ReportOut])
def my_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    reports = (
        db.query(Report)
        .filter(Report.owner_user_id == user.id)
        .order_by(Report.updated_at.desc())
        .all()
    )
    return [serialize(r) for r in reports]


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    # Author may only create reports targeting a domain they belong to.
    try:
        domain = Domain(payload.target_domain)
    except ValueError:
        raise HTTPException(422, "Invalid target_domain")
    if not principal.can_author_in(domain):
        audit(
            db, user_email=user.email, action="create_report", allowed=False,
            detail=f"not authorized to author in {domain.value}",
        )
        raise HTTPException(403, f"You are not a member of {domain.label}")

    folder = _personal_folder(db, user)
    report = Report(
        title=payload.title,
        description=payload.description,
        dashboard_type=payload.dashboard_type,
        status=ReportStatus.DRAFT,
        folder_id=folder.id,
        owner_user_id=user.id,
        target_domain=domain.value,
        config=payload.config,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    audit(db, user_email=user.email, action="create_report", resource_type="report",
          resource_id=report.id)
    return serialize(report)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Not found")
    authz.assert_can_view_report(principal, user, report)
    return serialize(report)


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Not found")
    authz.assert_can_edit_report(principal, user, report)
    if payload.title is not None:
        report.title = payload.title
    if payload.description is not None:
        report.description = payload.description
    if payload.config is not None:
        report.config = payload.config
    if payload.target_domain is not None:
        try:
            domain = Domain(payload.target_domain)
        except ValueError:
            raise HTTPException(422, "Invalid target_domain")
        if not principal.can_author_in(domain):
            raise HTTPException(403, f"You are not a member of {domain.label}")
        report.target_domain = domain.value
    db.commit()
    db.refresh(report)
    return serialize(report)


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: int,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Not found")
    authz.assert_can_edit_report(principal, user, report)
    db.delete(report)
    db.commit()


# --------------------------------------------------------------------------- #
# Publishing workflow
# --------------------------------------------------------------------------- #
@router.post("/{report_id}/submit", response_model=ReportOut)
def submit_for_review(
    report_id: int,
    payload: PublishRequest,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Not found")
    domain = authz.assert_can_request_publish(principal, user, report)

    report.status = ReportStatus.IN_REVIEW
    db.add(
        ApprovalRequest(
            report_id=report.id,
            target_domain=domain.value,
            requested_by_id=user.id,
            decision=ApprovalDecision.PENDING,
            comment=payload.comment,
        )
    )
    db.commit()
    db.refresh(report)
    audit(db, user_email=user.email, action="submit_review", resource_type="report",
          resource_id=report.id, detail=f"target={domain.value}")
    return serialize(report)


@router.get("/approvals/queue", response_model=list[ApprovalQueueItem])
def approval_queue(
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApprovalQueueItem]:
    """Pending publish requests for the domains the caller can approve."""
    approver_domains = {
        d.value for d in principal.domains if principal.can_approve_for(d)
    }
    if not approver_domains:
        return []
    pending = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.decision == ApprovalDecision.PENDING,
            ApprovalRequest.target_domain.in_(approver_domains),
        )
        .all()
    )
    return [
        ApprovalQueueItem(
            approval_id=a.id,
            target_domain=a.target_domain,
            requested_by=a.report.owner.email,
            comment=a.comment,
            created_at=a.created_at,
            report=serialize(a.report),
        )
        for a in pending
    ]


@router.post("/approvals/{approval_id}/decide", response_model=ReportOut)
def decide_approval(
    approval_id: int,
    payload: ApprovalDecisionIn,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    approval = db.get(ApprovalRequest, approval_id)
    if approval is None or approval.decision != ApprovalDecision.PENDING:
        raise HTTPException(404, "No pending approval")
    domain = Domain(approval.target_domain)
    authz.assert_can_decide_publish(principal, domain)  # 403 if not an approver

    report = approval.report
    approval.reviewer_id = user.id
    approval.comment = payload.comment or approval.comment
    approval.decided_at = datetime.now(timezone.utc)

    if payload.approve:
        approval.decision = ApprovalDecision.APPROVED
        report.status = ReportStatus.PUBLISHED
        report.folder_id = _domain_folder(db, domain).id  # move into domain workspace
        report.published_at = datetime.now(timezone.utc)
        action = "approve_publish"
    else:
        approval.decision = ApprovalDecision.REJECTED
        report.status = ReportStatus.CHANGES_REQUESTED  # back to the author
        action = "reject_publish"

    db.commit()
    db.refresh(report)
    audit(db, user_email=user.email, action=action, resource_type="report",
          resource_id=report.id, detail=f"domain={domain.value}")
    return serialize(report)
