"""Folder navigation — the access-controlled tree of the portal shell."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_principal, get_current_user
from ...auth.rbac import Domain, Principal
from ...models import Folder, FolderType, User
from ...database import get_db
from ...schemas import FolderOut, ReportOut
from ...services import authz

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _to_out(folder: Folder, principal: Principal, report_count: int) -> FolderOut:
    can_author = False
    if folder.type == FolderType.DOMAIN and folder.domain:
        can_author = principal.can_author_in(Domain(folder.domain))
    elif folder.type == FolderType.PERSONAL:
        can_author = True
    return FolderOut(
        id=folder.id,
        name=folder.name,
        slug=folder.slug,
        description=folder.description,
        type=folder.type,
        domain=folder.domain,
        report_count=report_count,
        can_author=can_author,
    )


@router.get("", response_model=list[FolderOut])
def list_folders(
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FolderOut]:
    """Only folders the caller is entitled to see (shared + their domains +
    their personal workspace)."""
    out: list[FolderOut] = []
    for folder in authz.visible_folders(db, principal, user):
        reports = [
            r
            for r in folder.reports
            if authz.can_view_report(principal, user, r)
        ]
        out.append(_to_out(folder, principal, len(reports)))
    # Stable ordering: shared, then domain, then personal.
    order = {FolderType.SHARED: 0, FolderType.DOMAIN: 1, FolderType.PERSONAL: 2}
    out.sort(key=lambda f: (order[FolderType(f.type)], f.name))
    return out


@router.get("/{slug}/reports", response_model=list[ReportOut])
def list_folder_reports(
    slug: str,
    principal: Principal = Depends(get_current_principal),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    folder = db.query(Folder).filter(Folder.slug == slug).first()
    if folder is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")
    # 404 (not 403) if the caller isn't entitled — don't leak existence.
    authz.assert_can_view_folder(principal, user, folder)
    reports = [r for r in folder.reports if authz.can_view_report(principal, user, r)]
    return [
        ReportOut(
            id=r.id,
            title=r.title,
            description=r.description,
            dashboard_type=r.dashboard_type,
            status=r.status,
            folder_id=r.folder_id,
            owner_email=r.owner.email,
            target_domain=r.target_domain,
            config=r.config,
            created_at=r.created_at,
            updated_at=r.updated_at,
            published_at=r.published_at,
        )
        for r in reports
    ]
