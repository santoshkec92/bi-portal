"""Idempotent seed: folder tree + demo content.

Creates:
  * one SHARED folder (visible to all authenticated users)
  * one DOMAIN folder per business function
  * the demo users (so seeded reports have real owners + personal workspaces)
  * published reports in Finance & Sales Ops domain folders
  * one draft and one in-review report to demonstrate the approval queue

Safe to run repeatedly; existing rows are left untouched.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .auth.okta import MOCK_USERS
from .auth.rbac import Domain
from .database import SessionLocal
from .models import (
    ApprovalDecision,
    ApprovalRequest,
    DashboardType,
    Folder,
    FolderType,
    Report,
    ReportStatus,
    User,
)
from .services.provisioning import upsert_user

_DOMAIN_FOLDERS = [
    (Domain.FINANCE, "Finance", "ARR, retention, and forecasting dashboards for Finance."),
    (Domain.SALES_OPS, "Sales Ops", "Pipeline, coverage, and forecast health for Sales Ops."),
    (Domain.REVOPS, "RevOps", "Cross-functional revenue operations dashboards."),
    (Domain.CUSTOMER_SUCCESS, "Customer Success", "Adoption, health, and renewal-risk dashboards."),
]


def _get_or_create_folder(db, **kwargs) -> Folder:
    slug = kwargs["slug"]
    folder = db.query(Folder).filter(Folder.slug == slug).first()
    if folder is None:
        folder = Folder(**kwargs)
        db.add(folder)
        db.flush()
    return folder


def seed() -> None:
    db = SessionLocal()
    try:
        # 1. Shared folder.
        shared = _get_or_create_folder(
            db,
            name="Shared",
            slug="shared",
            description="Company-wide dashboards visible to everyone.",
            type=FolderType.SHARED,
            domain=None,
        )

        # 2. Domain folders.
        domain_folders: dict[str, Folder] = {}
        for domain, name, desc in _DOMAIN_FOLDERS:
            domain_folders[domain.value] = _get_or_create_folder(
                db,
                name=name,
                slug=f"domain-{domain.value}",
                description=desc,
                type=FolderType.DOMAIN,
                domain=domain.value,
            )
        db.commit()

        # 3. Demo users + their personal workspaces.
        users: dict[str, User] = {}
        for key, claims in MOCK_USERS.items():
            users[key] = upsert_user(db, claims)

        # 4. Demo published reports (idempotent by title+folder).
        def ensure_published(title, dtype, folder, owner, target, config):
            existing = (
                db.query(Report)
                .filter(Report.title == title, Report.folder_id == folder.id)
                .first()
            )
            if existing:
                return existing
            r = Report(
                title=title,
                description="",
                dashboard_type=dtype,
                status=ReportStatus.PUBLISHED,
                folder_id=folder.id,
                owner_user_id=owner.id,
                target_domain=target.value,
                config=config,
                published_at=datetime.now(timezone.utc),
            )
            db.add(r)
            db.flush()
            db.add(
                ApprovalRequest(
                    report_id=r.id,
                    target_domain=target.value,
                    requested_by_id=owner.id,
                    decision=ApprovalDecision.APPROVED,
                    reviewer_id=owner.id,
                    comment="Seed approval",
                    decided_at=datetime.now(timezone.utc),
                )
            )
            return r

        ensure_published(
            "ARR Waterfall — FY26-Q1",
            DashboardType.ARR_WATERFALL,
            domain_folders[Domain.FINANCE.value],
            users["fiona"],
            Domain.FINANCE,
            {"period": "FY26-Q1", "segment": None},
        )
        ensure_published(
            "Pipeline Health — FY26-Q2",
            DashboardType.PIPELINE_HEALTH,
            domain_folders[Domain.SALES_OPS.value],
            users["sam"],
            Domain.SALES_OPS,
            {"quarter": "FY26-Q2", "team": None},
        )
        # Company-wide exec view in the Shared folder.
        ensure_published(
            "Company ARR Snapshot",
            DashboardType.ARR_WATERFALL,
            shared,
            users["ada"],
            Domain.FINANCE,
            {"period": "FY26-Q1", "segment": "Enterprise"},
        )

        # A draft in Frank's personal workspace.
        frank = users["frank"]
        frank_personal = (
            db.query(Folder)
            .filter(Folder.type == FolderType.PERSONAL, Folder.owner_user_id == frank.id)
            .first()
        )
        if not db.query(Report).filter(
            Report.title == "Draft: Enterprise ARR deep-dive",
            Report.owner_user_id == frank.id,
        ).first():
            db.add(
                Report(
                    title="Draft: Enterprise ARR deep-dive",
                    dashboard_type=DashboardType.ARR_WATERFALL,
                    status=ReportStatus.DRAFT,
                    folder_id=frank_personal.id,
                    owner_user_id=frank.id,
                    target_domain=Domain.FINANCE.value,
                    config={"period": "FY26-Q1", "segment": "Enterprise"},
                )
            )

        # An in-review report awaiting Fiona's approval (Finance approver).
        if not db.query(Report).filter(
            Report.title == "Review: SMB churn watch",
            Report.owner_user_id == frank.id,
        ).first():
            review_report = Report(
                title="Review: SMB churn watch",
                dashboard_type=DashboardType.ARR_WATERFALL,
                status=ReportStatus.IN_REVIEW,
                folder_id=frank_personal.id,
                owner_user_id=frank.id,
                target_domain=Domain.FINANCE.value,
                config={"period": "FY26-Q1", "segment": "SMB"},
            )
            db.add(review_report)
            db.flush()
            db.add(
                ApprovalRequest(
                    report_id=review_report.id,
                    target_domain=Domain.FINANCE.value,
                    requested_by_id=frank.id,
                    decision=ApprovalDecision.PENDING,
                    comment="Please review for publishing to Finance.",
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    from .database import init_db

    init_db()
    seed()
    print("Seed complete.")
