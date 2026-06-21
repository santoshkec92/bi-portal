"""Just-in-time provisioning and audit logging."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..auth.okta import TokenClaims
from ..models import AuditEvent, Folder, FolderType, User


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def upsert_user(db: Session, claims: TokenClaims) -> User:
    """Create or refresh the user on login, and ensure their personal folder."""
    user = db.query(User).filter(User.okta_sub == claims.sub).first()
    if user is None:
        user = User(okta_sub=claims.sub, email=claims.email, name=claims.name)
        db.add(user)
        db.flush()  # assign id
    else:
        user.email = claims.email
        user.name = claims.name
    user.last_login_at = datetime.now(timezone.utc)

    # Ensure a personal workspace folder exists for this user.
    personal = (
        db.query(Folder)
        .filter(Folder.type == FolderType.PERSONAL, Folder.owner_user_id == user.id)
        .first()
    )
    if personal is None:
        db.add(
            Folder(
                name=f"{claims.name.split('(')[0].strip()}'s Workspace",
                slug=f"personal-{_slugify(claims.email)}",
                description="Your private drafting area. Reports here are visible only to you.",
                type=FolderType.PERSONAL,
                owner_user_id=user.id,
            )
        )
    db.commit()
    db.refresh(user)
    return user


def audit(
    db: Session,
    *,
    user_email: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    allowed: bool = True,
    detail: str = "",
) -> None:
    db.add(
        AuditEvent(
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            allowed=allowed,
            detail=detail,
        )
    )
    db.commit()
