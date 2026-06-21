"""Current-user identity + effective permissions."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...auth.dependencies import get_current_principal
from ...auth.rbac import Principal
from ...schemas import DomainRoleOut, MeOut

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeOut)
def me(principal: Principal = Depends(get_current_principal)) -> MeOut:
    return MeOut(
        sub=principal.sub,
        email=principal.email,
        name=principal.name,
        is_admin=principal.is_admin,
        groups=list(principal.raw_groups),
        domains=[
            DomainRoleOut(domain=d.value, domain_label=d.label, role=r.value)
            for d, r in principal.domain_roles.items()
        ],
    )
