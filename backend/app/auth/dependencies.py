"""FastAPI dependencies: authentication + the Principal injection point.

`get_current_principal` is the gate every protected route passes through. It
reconstructs the verified identity from the signed session cookie and converts
it into an authorization `Principal`. Routes then layer resource-level checks
on top (see `services/authz.py`).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from .rbac import Principal, principal_from_claims
from .session import read_session


def get_current_principal(request: Request) -> Principal:
    session = read_session(request)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal_from_claims(
        sub=session["sub"],
        email=session["email"],
        name=session["name"],
        groups=session.get("groups", []),
    )


def get_current_user(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the DB User row for the authenticated principal.

    Users are provisioned just-in-time on first authenticated request, so we
    never need an out-of-band sync from Okta.
    """
    user = db.query(User).filter(User.okta_sub == principal.sub).first()
    if user is None:
        raise HTTPException(status_code=403, detail="User not provisioned")
    return user
