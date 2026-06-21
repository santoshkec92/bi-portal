"""Unit tests for the RBAC core — the most security-critical module."""
from __future__ import annotations

from app.auth.rbac import Domain, Role, principal_from_claims


def test_admin_sees_all_domains():
    p = principal_from_claims("s", "a@x.com", "Ada", ["BI-Portal-Admin"])
    assert p.is_admin
    assert p.domains == set(Domain)
    assert p.can_approve_for(Domain.FINANCE)
    assert p.can_author_in(Domain.SALES_OPS)


def test_domain_member_is_author_only():
    p = principal_from_claims("s", "f@x.com", "Frank", ["BI-Finance"])
    assert p.in_domain(Domain.FINANCE)
    assert not p.in_domain(Domain.SALES_OPS)
    assert p.can_author_in(Domain.FINANCE)
    assert not p.can_approve_for(Domain.FINANCE)


def test_approver_suffix_elevates_role():
    p = principal_from_claims(
        "s", "fi@x.com", "Fiona", ["BI-Finance", "BI-Finance-Approver"]
    )
    assert p.role_in(Domain.FINANCE) == Role.APPROVER
    assert p.can_approve_for(Domain.FINANCE)


def test_no_groups_means_no_domains():
    p = principal_from_claims("s", "n@x.com", "Nina", [])
    assert p.domains == set()
    assert not p.in_domain(Domain.FINANCE)


def test_unknown_groups_are_ignored():
    p = principal_from_claims("s", "x@x.com", "X", ["Some-Other-App-Group"])
    assert p.domains == set()
