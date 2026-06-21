"""End-to-end RBAC tests through the HTTP layer (mock auth mode).

These prove the key requirement: a user not in a domain cannot list, open, or
render that domain's dashboards — even with a direct URL.
"""
from __future__ import annotations

import os

os.environ.setdefault("AUTH_MODE", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bi_portal.db")
os.environ.setdefault("SEED_ON_STARTUP", "true")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, user: str) -> TestClient:
    resp = client.post(f"/api/auth/mock-login?user={user}")
    assert resp.status_code == 200, resp.text
    return client


def test_unauthenticated_is_rejected(client):
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/folders").status_code == 401


def test_finance_user_sees_finance_not_salesops(client):
    login(client, "frank")  # BI-Finance only
    folders = client.get("/api/folders").json()
    slugs = {f["slug"] for f in folders}
    assert "domain-finance" in slugs
    assert "shared" in slugs
    assert "domain-sales_ops" not in slugs  # not a member


def test_cross_domain_direct_url_is_404(client):
    # Sales Ops published report should be invisible to a Finance-only user,
    # even by guessing the report id.
    login(client, "sam")  # Sales Ops
    sam_reports = client.get("/api/folders/domain-sales_ops/reports").json()
    assert sam_reports, "expected a seeded Sales Ops report"
    sales_report_id = sam_reports[0]["id"]

    login(client, "frank")  # Finance only
    # Cannot list Sales Ops folder...
    assert client.get("/api/folders/domain-sales_ops/reports").status_code == 404
    # ...and cannot render the dashboard by direct id.
    assert client.get(f"/api/dashboards/{sales_report_id}").status_code == 404
    assert client.get(f"/api/reports/{sales_report_id}").status_code == 404


def test_only_approver_sees_approval_queue(client):
    login(client, "frank")  # author, not approver
    assert client.get("/api/reports/approvals/queue").json() == []

    login(client, "fiona")  # Finance approver
    queue = client.get("/api/reports/approvals/queue").json()
    assert any(r["title"] == "Review: SMB churn watch" for r in queue)


def test_dashboard_renders_with_insight(client):
    login(client, "fiona")
    finance = client.get("/api/folders/domain-finance/reports").json()
    rid = finance[0]["id"]
    dash = client.get(f"/api/dashboards/{rid}").json()
    assert dash["data"]["bridge"]
    assert dash["insight"]["headline"]
    assert dash["insight_backend"].startswith(("mock", "claude"))
