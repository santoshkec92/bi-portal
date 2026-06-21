"""Okta OAuth 2.0 / OIDC — Authorization Code flow with PKCE.

Why Authorization Code + PKCE (and not implicit / client-credentials):
* The portal is a confidential-ish web app but we use PKCE so the flow is safe
  even if the client secret is unavailable (public client) — this is the
  modern OAuth 2.1 recommendation and removes a class of code-interception
  attacks.
* `state` protects against CSRF on the redirect; `nonce` binds the id_token to
  this login attempt; the PKCE `code_verifier` binds the token exchange to the
  browser that started it.

We rely on Okta's OIDC discovery document so endpoints are not hard-coded.
Group memberships arrive in the `groups` claim of the id_token (configure an
Okta "Groups claim" on the authorization server) and are the input to RBAC.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

import httpx
from jose import jwt

from ..config import settings


@dataclass
class TokenClaims:
    sub: str
    email: str
    name: str
    groups: list[str]


@dataclass
class PkceChallenge:
    verifier: str
    challenge: str
    state: str
    nonce: str


def generate_pkce() -> PkceChallenge:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return PkceChallenge(
        verifier=verifier,
        challenge=challenge,
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
    )


class OktaClient:
    """Thin async client around the Okta OIDC endpoints."""

    def __init__(self) -> None:
        self._discovery: dict | None = None
        self._jwks: dict | None = None

    async def _discover(self) -> dict:
        if self._discovery is None:
            url = f"{settings.okta_issuer.rstrip('/')}/.well-known/openid-configuration"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                self._discovery = resp.json()
        return self._discovery

    async def _get_jwks(self) -> dict:
        if self._jwks is None:
            disc = await self._discover()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(disc["jwks_uri"])
                resp.raise_for_status()
                self._jwks = resp.json()
        return self._jwks

    async def authorization_url(self, pkce: PkceChallenge) -> str:
        disc = await self._discover()
        from urllib.parse import urlencode

        params = {
            "client_id": settings.okta_client_id,
            "response_type": "code",
            "scope": settings.okta_scopes,
            "redirect_uri": settings.redirect_uri,
            "state": pkce.state,
            "nonce": pkce.nonce,
            "code_challenge": pkce.challenge,
            "code_challenge_method": "S256",
        }
        return f"{disc['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(self, code: str, verifier: str) -> dict:
        disc = await self._discover()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.redirect_uri,
            "client_id": settings.okta_client_id,
            "code_verifier": verifier,
        }
        # Confidential clients also send the secret; public PKCE clients omit it.
        auth = None
        if settings.okta_client_secret:
            auth = (settings.okta_client_id, settings.okta_client_secret)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(disc["token_endpoint"], data=data, auth=auth)
            resp.raise_for_status()
            return resp.json()

    async def verify_id_token(self, id_token: str, nonce: str) -> TokenClaims:
        disc = await self._discover()
        jwks = await self._get_jwks()
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.okta_client_id,
            issuer=disc["issuer"],
            options={"verify_at_hash": False},
        )
        if claims.get("nonce") != nonce:
            raise ValueError("OIDC nonce mismatch — possible replay attack")
        groups = claims.get(settings.okta_groups_claim, []) or []
        return TokenClaims(
            sub=claims["sub"],
            email=claims.get("email", claims["sub"]),
            name=claims.get("name", claims.get("email", "Unknown")),
            groups=list(groups),
        )


okta_client = OktaClient()


# --------------------------------------------------------------------------- #
# Mock identity provider (AUTH_MODE=mock)
# --------------------------------------------------------------------------- #
# A roster of synthetic users that exercise every RBAC path, so the entire
# portal — folders, domain isolation, publishing approvals — is demoable with
# zero external dependencies. These map 1:1 to the group convention in rbac.py.
MOCK_USERS: dict[str, TokenClaims] = {
    "fiona": TokenClaims(
        sub="okta|mock-fiona",
        email="fiona.finance@acme.com",
        name="Fiona (Finance Approver)",
        groups=["BI-Finance", "BI-Finance-Approver"],
    ),
    "frank": TokenClaims(
        sub="okta|mock-frank",
        email="frank.analyst@acme.com",
        name="Frank (Finance Analyst)",
        groups=["BI-Finance"],
    ),
    "sam": TokenClaims(
        sub="okta|mock-sam",
        email="sam.salesops@acme.com",
        name="Sam (Sales Ops Approver)",
        groups=["BI-SalesOps", "BI-SalesOps-Approver"],
    ),
    "rita": TokenClaims(
        sub="okta|mock-rita",
        email="rita.revops@acme.com",
        name="Rita (RevOps)",
        groups=["BI-RevOps"],
    ),
    "casey": TokenClaims(
        sub="okta|mock-casey",
        email="casey.cs@acme.com",
        name="Casey (Customer Success)",
        groups=["BI-CustomerSuccess"],
    ),
    "ada": TokenClaims(
        sub="okta|mock-ada",
        email="ada.admin@acme.com",
        name="Ada (Platform Admin)",
        groups=["BI-Portal-Admin"],
    ),
    "nina": TokenClaims(
        sub="okta|mock-nina",
        email="nina.newhire@acme.com",
        name="Nina (No domain groups)",
        groups=[],
    ),
}
