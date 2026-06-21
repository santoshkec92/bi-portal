"""Data model for the portal's governance layer.

Design notes
------------
* **Folders** are the unit of access control. Three kinds exist:
    - SHARED   : visible to every authenticated user (read-only common ground).
    - DOMAIN   : owned by a business function (finance, sales_ops, ...). Only
                 members of that domain may list/open reports inside it.
    - PERSONAL : a single user's private drafting area. Only the owner sees it.
* **Reports** are dashboards. They are born in a PERSONAL folder (status DRAFT),
  go through a review/approval workflow, and on approval are *published* into
  the author's DOMAIN folder.
* **ApprovalRequest** records the publishing workflow as an explicit, auditable
  state machine rather than a boolean flag.
* **AuditEvent** captures security-relevant actions (logins, denied access,
  publishes) so RBAC decisions are observable.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class FolderType(str, enum.Enum):
    SHARED = "shared"
    DOMAIN = "domain"
    PERSONAL = "personal"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"                      # private, in personal workspace
    IN_REVIEW = "in_review"              # submitted, awaiting domain approval
    CHANGES_REQUESTED = "changes_requested"
    PUBLISHED = "published"              # live in the domain workspace
    ARCHIVED = "archived"


class DashboardType(str, enum.Enum):
    ARR_WATERFALL = "arr_waterfall"
    PIPELINE_HEALTH = "pipeline_health"


class ApprovalDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable Okta subject identifier (`sub` claim). Unique per identity.
    okta_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    folders: Mapped[list["Folder"]] = relationship(back_populates="owner")
    reports: Mapped[list["Report"]] = relationship(back_populates="owner")


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("slug", name="uq_folder_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[FolderType] = mapped_column(Enum(FolderType), index=True)
    # For DOMAIN folders: the business-function key (e.g. "finance").
    domain: Mapped[str | None] = mapped_column(String(64), index=True)
    # For PERSONAL folders: the owning user.
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["User | None"] = relationship(back_populates="folders")
    reports: Mapped[list["Report"]] = relationship(back_populates="folder")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    dashboard_type: Mapped[DashboardType] = mapped_column(Enum(DashboardType))
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.DRAFT, index=True
    )

    # Where the report currently lives (personal while drafting, domain once
    # published). target_domain is the function it is intended to publish to.
    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id"), index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_domain: Mapped[str | None] = mapped_column(String(64), index=True)

    # Dashboard parameters (date range, segment filters, etc).
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    folder: Mapped["Folder"] = relationship(back_populates="reports")
    owner: Mapped["User"] = relationship(back_populates="reports")
    approvals: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ApprovalRequest(Base):
    """One row per publish attempt. Models the review workflow explicitly."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    target_domain: Mapped[str] = mapped_column(String(64), index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[ApprovalDecision] = mapped_column(
        Enum(ApprovalDecision), default=ApprovalDecision.PENDING, index=True
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report: Mapped["Report"] = relationship(back_populates="approvals")


class AuditEvent(Base):
    """Append-only security/audit log."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str | None] = mapped_column(String(320), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    allowed: Mapped[bool] = mapped_column(default=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
