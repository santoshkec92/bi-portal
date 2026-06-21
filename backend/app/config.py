"""Central application configuration.

All settings are sourced from environment variables (12-factor). In containers
these are injected from the platform's native secret manager (K8s Secrets /
Snowflake SECRET objects) — never baked into the image. See `deploy/`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ------------------------------------------------------------------ app
    app_name: str = "Centralized BI Portal"
    environment: Literal["development", "staging", "production"] = "development"
    # Public base URL of the app (used to build the OAuth redirect URI).
    base_url: str = "http://localhost:8000"
    # Comma-separated list of allowed CORS origins (frontend dev server, etc).
    cors_origins: str = "http://localhost:5173,http://localhost:8000"

    # -------------------------------------------------------------- sessions
    # Used to sign the session cookie. MUST be overridden in production.
    session_secret: str = "dev-only-insecure-change-me"
    session_cookie_name: str = "bi_portal_session"
    session_max_age_seconds: int = 60 * 60 * 8  # 8h

    # ------------------------------------------------------------------ auth
    # "okta" = real Authorization Code + PKCE flow against an Okta tenant.
    # "mock" = local dev login that mints sessions for synthetic users so the
    #          full RBAC stack is demoable with zero external dependencies.
    auth_mode: Literal["okta", "mock"] = "mock"

    okta_issuer: str = ""           # e.g. https://dev-123.okta.com/oauth2/default
    okta_client_id: str = ""
    okta_client_secret: str = ""    # optional for public PKCE clients
    okta_scopes: str = "openid profile email groups"
    # Name of the claim that carries the user's group memberships.
    okta_groups_claim: str = "groups"

    # ------------------------------------------------------------- database
    # Portal metadata store. SQLite by default (zero-config); swap to Postgres
    # in prod via DATABASE_URL=postgresql+psycopg2://user:pass@host/db
    database_url: str = "sqlite:///./bi_portal.db"

    # ----------------------------------------------------------- claude / llm
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-latest"
    claude_max_tokens: int = 1024
    # When no API key is present we fall back to a deterministic local
    # "insight" generator so dashboards still render in demos/offline.
    claude_mock_when_unconfigured: bool = True

    # ------------------------------------------------------------- snowflake
    # All optional. When unset, dashboards use the synthetic dataset generator.
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = "ANALYTICS"
    snowflake_role: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/auth/callback"

    @property
    def snowflake_configured(self) -> bool:
        return bool(self.snowflake_account and self.snowflake_user)

    @property
    def claude_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
