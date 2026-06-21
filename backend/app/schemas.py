"""Pydantic request/response models (the public API contract)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .models import DashboardType, FolderType, ReportStatus


class DomainRoleOut(BaseModel):
    domain: str
    domain_label: str
    role: str


class MeOut(BaseModel):
    sub: str
    email: str
    name: str
    is_admin: bool
    groups: list[str]
    domains: list[DomainRoleOut]


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    type: FolderType
    domain: str | None
    report_count: int = 0
    can_author: bool = False


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    target_domain: str
    decision: str
    comment: str
    created_at: datetime
    decided_at: datetime | None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    dashboard_type: DashboardType
    status: ReportStatus
    folder_id: int
    owner_email: str
    target_domain: str | None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class ReportCreate(BaseModel):
    title: str
    description: str = ""
    dashboard_type: DashboardType
    target_domain: str
    config: dict[str, Any] = {}


class ReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    target_domain: str | None = None


class PublishRequest(BaseModel):
    comment: str = ""


class ApprovalDecisionIn(BaseModel):
    approve: bool
    comment: str = ""


class ApprovalQueueItem(BaseModel):
    approval_id: int
    target_domain: str
    requested_by: str
    comment: str
    created_at: datetime
    report: ReportOut


class InsightOut(BaseModel):
    headline: str
    narrative: str
    key_findings: list[str]
    risks: list[str]
    recommended_actions: list[str]
    generated_by: str


class DashboardOut(BaseModel):
    dashboard_type: str
    title: str
    data: dict[str, Any]
    insight: InsightOut
    data_backend: str
    insight_backend: str


class MockUserOut(BaseModel):
    key: str
    name: str
    email: str
    groups: list[str]
