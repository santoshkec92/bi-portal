"""Authentication routes: Okta Authorization Code + PKCE, plus mock-mode login.

Flow (okta mode):
    GET  /api/auth/login     -> 302 to Okta /authorize (with PKCE challenge)
    GET  /api/auth/callback  -> exchange code, verify id_token, set session
    POST /api/auth/logout    -> clear session

Flow (mock mode): GET /api/auth/mock-users lists synthetic identities and
POST /api/auth/mock-login?user=fiona mints a session for one. Same downstream
RBAC, no external IdP required.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...auth.okta import MOCK_USERS, TokenClaims, generate_pkce, okta_client
from ...auth.session import (
    clear_oauth_tx,
    clear_session,
    read_oauth_tx,
    write_oauth_tx,
    write_session,
)
from ...config import settings
from ...database import get_db
from ...schemas import MockUserOut
from ...services.provisioning import audit, upsert_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _establish_session(response: Response, db: Session, claims: TokenClaims) -> None:
    upsert_user(db, claims)
    write_session(
        response,
        {
            "sub": claims.sub,
            "email": claims.email,
            "name": claims.name,
            "groups": claims.groups,
        },
    )
    audit(db, user_email=claims.email, action="login", detail=f"groups={claims.groups}")


@router.get("/config")
def auth_config() -> dict:
    """Tells the frontend which auth UI to render."""
    return {"auth_mode": settings.auth_mode, "app_name": settings.app_name}


# --------------------------------------------------------------------------- #
# Okta (Authorization Code + PKCE)
# --------------------------------------------------------------------------- #
@router.get("/login")
async def login(request: Request):
    if settings.auth_mode != "okta":
        raise HTTPException(400, "Okta login disabled (AUTH_MODE != okta)")
    pkce = generate_pkce()
    auth_url = await okta_client.authorization_url(pkce)
    redirect = RedirectResponse(auth_url, status_code=302)
    # Carry verifier/state/nonce across the redirect in a short-lived signed cookie.
    write_oauth_tx(
        redirect, {"verifier": pkce.verifier, "state": pkce.state, "nonce": pkce.nonce}
    )
    return redirect


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if settings.auth_mode != "okta":
        raise HTTPException(400, "Okta login disabled")
    tx = read_oauth_tx(request)
    if not tx or tx.get("state") != state:
        raise HTTPException(400, "Invalid OAuth state (possible CSRF)")

    tokens = await okta_client.exchange_code(code, tx["verifier"])
    claims = await okta_client.verify_id_token(tokens["id_token"], tx["nonce"])

    # Redirect to the SPA root with the session cookie attached.
    redirect = RedirectResponse(url="/", status_code=302)
    _establish_session(redirect, db, claims)
    clear_oauth_tx(redirect)
    return redirect


# --------------------------------------------------------------------------- #
# Mock mode
# --------------------------------------------------------------------------- #
@router.get("/mock-users", response_model=list[MockUserOut])
def mock_users() -> list[MockUserOut]:
    if settings.auth_mode != "mock":
        raise HTTPException(400, "Mock login disabled (AUTH_MODE != mock)")
    return [
        MockUserOut(key=k, name=v.name, email=v.email, groups=v.groups)
        for k, v in MOCK_USERS.items()
    ]


@router.post("/mock-login")
def mock_login(
    response: Response,
    user: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    if settings.auth_mode != "mock":
        raise HTTPException(400, "Mock login disabled")
    claims = MOCK_USERS.get(user)
    if claims is None:
        raise HTTPException(404, f"Unknown mock user '{user}'")
    _establish_session(response, db, claims)
    return {"ok": True, "email": claims.email}


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db)) -> dict:
    clear_session(response)
    return {"ok": True}
