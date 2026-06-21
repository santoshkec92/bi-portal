"""Role-Based Access Control core.

This module is the single source of truth for *who can do what*. Everything
upstream (routers, dependencies) and the UI defer to the predicates defined
here. Keeping authorization logic in one cohesive, unit-testable module — rather
than scattering `if "Finance" in groups` checks across endpoints — is the main
architectural decision of the RBAC layer.

Identity → authorization mapping
--------------------------------
Okta is the source of *identity* and *group membership*. We translate raw Okta
group names into portal concepts (domains + roles) using a small, declarative
mapping. This decoupling means: rename an Okta group, change one line here;
endpoints never hard-code group strings.

Group naming convention (configurable via GROUP_MAP):
    BI-Portal-Admin            -> platform admin (superuser)
    BI-Finance                 -> member of the `finance` domain
    BI-Finance-Approver        -> approver for the `finance` domain
    BI-SalesOps                -> member of the `sales_ops` domain
    ... etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Domain(str, Enum):
    """Business functions, each with a dedicated Domain Workspace folder."""

    FINANCE = "finance"
    SALES_OPS = "sales_ops"
    REVOPS = "revops"
    CUSTOMER_SUCCESS = "customer_success"

    @property
    def label(self) -> str:
        return {
            "finance": "Finance",
            "sales_ops": "Sales Ops",
            "revops": "RevOps",
            "customer_success": "Customer Success",
        }[self.value]


class Role(str, Enum):
    """Capability tier *within* a domain (or platform-wide for ADMIN)."""

    VIEWER = "viewer"      # can list/open/query published reports in the domain
    AUTHOR = "author"      # + can draft reports and request publishing
    APPROVER = "approver"  # + can approve/reject publish requests
    ADMIN = "admin"        # platform superuser, all domains


# Declarative Okta-group -> (domain, role) mapping.
# A single Okta group can imply membership; the "-Approver" suffix elevates role.
GROUP_TO_DOMAIN: dict[str, Domain] = {
    "BI-Finance": Domain.FINANCE,
    "BI-SalesOps": Domain.SALES_OPS,
    "BI-RevOps": Domain.REVOPS,
    "BI-CustomerSuccess": Domain.CUSTOMER_SUCCESS,
}

ADMIN_GROUP = "BI-Portal-Admin"
APPROVER_SUFFIX = "-Approver"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, derived from the verified Okta token.

    Created once per request from the session and passed everywhere. Treat it
    as immutable; never mutate authorization state mid-request.
    """

    sub: str
    email: str
    name: str
    raw_groups: tuple[str, ...] = ()
    # domain -> highest role the user holds in that domain
    domain_roles: dict[Domain, Role] = field(default_factory=dict)
    is_admin: bool = False

    # ---------------------------------------------------------------- queries
    @property
    def domains(self) -> set[Domain]:
        if self.is_admin:
            return set(Domain)
        return set(self.domain_roles.keys())

    def in_domain(self, domain: Domain) -> bool:
        return self.is_admin or domain in self.domain_roles

    def role_in(self, domain: Domain) -> Role | None:
        if self.is_admin:
            return Role.ADMIN
        return self.domain_roles.get(domain)

    def can_author_in(self, domain: Domain) -> bool:
        role = self.role_in(domain)
        return role in (Role.AUTHOR, Role.APPROVER, Role.ADMIN)

    def can_approve_for(self, domain: Domain) -> bool:
        role = self.role_in(domain)
        return role in (Role.APPROVER, Role.ADMIN)


def principal_from_claims(
    sub: str, email: str, name: str, groups: list[str]
) -> Principal:
    """Translate verified token claims into a Principal.

    The `groups` list comes from the Okta `groups` claim (verified as part of
    the signed id_token / introspection). This is the *only* place raw group
    strings are interpreted.
    """
    is_admin = ADMIN_GROUP in groups
    domain_roles: dict[Domain, Role] = {}

    for g in groups:
        # Approver groups look like "BI-Finance-Approver".
        base = g[: -len(APPROVER_SUFFIX)] if g.endswith(APPROVER_SUFFIX) else g
        domain = GROUP_TO_DOMAIN.get(base)
        if domain is None:
            continue
        role = Role.APPROVER if g.endswith(APPROVER_SUFFIX) else Role.AUTHOR
        # Keep the highest role seen for the domain.
        current = domain_roles.get(domain)
        if current is None or _role_rank(role) > _role_rank(current):
            domain_roles[domain] = role

    return Principal(
        sub=sub,
        email=email,
        name=name,
        raw_groups=tuple(groups),
        domain_roles=domain_roles,
        is_admin=is_admin,
    )


def _role_rank(role: Role) -> int:
    return {Role.VIEWER: 0, Role.AUTHOR: 1, Role.APPROVER: 2, Role.ADMIN: 3}[role]
