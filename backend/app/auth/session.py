"""Stateless, signed session cookies.

We deliberately avoid server-side session storage: after the OAuth exchange we
persist only the *minimal* verified identity (sub/email/name/groups) into a
cookie signed with `SESSION_SECRET` (itsdangerous). This keeps the app
horizontally scalable (no sticky sessions / shared session store needed) and
makes the trust boundary explicit — the cookie is integrity-protected and
short-lived.

Trade-off: signed (not encrypted) means contents are readable by the client.
We only store non-sensitive identity claims, never tokens. For revocation
needs at scale, swap this for a Redis-backed session id (see FUTURE_WORK).
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import settings

_serializer = URLSafeTimedSerializer(settings.session_secret, salt="bi-portal-session")


def write_session(response: Response, data: dict[str, Any]) -> None:
    token = _serializer.dumps(json.dumps(data))
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,                       # not readable by JS (XSS hardening)
        secure=settings.environment != "development",
        samesite="lax",                      # CSRF hardening for top-level nav
        path="/",
    )


def read_session(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    try:
        payload = _serializer.loads(raw, max_age=settings.session_max_age_seconds)
        return json.loads(payload)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def clear_session(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


# Short-lived cookie used to carry the PKCE verifier + state across the redirect.
_oauth_serializer = URLSafeTimedSerializer(settings.session_secret, salt="bi-portal-oauth")
_OAUTH_TX_COOKIE = "bi_portal_oauth_tx"


def write_oauth_tx(response: Response, data: dict[str, Any]) -> None:
    response.set_cookie(
        key=_OAUTH_TX_COOKIE,
        value=_oauth_serializer.dumps(json.dumps(data)),
        max_age=600,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        path="/",
    )


def read_oauth_tx(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(_OAUTH_TX_COOKIE)
    if not raw:
        return None
    try:
        return json.loads(_oauth_serializer.loads(raw, max_age=600))
    except (BadSignature, SignatureExpired, ValueError):
        return None


def clear_oauth_tx(response: Response) -> None:
    response.delete_cookie(_OAUTH_TX_COOKIE, path="/")
