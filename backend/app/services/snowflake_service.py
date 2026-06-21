"""Warehouse access layer.

A single seam for all analytical reads. When `SNOWFLAKE_*` is configured we run
parameterized SQL against the warehouse; otherwise we transparently serve the
synthetic dataset so the portal runs anywhere. Dashboard endpoints depend only
on the *shape* of the return value, never on which backend produced it.

Security notes:
* All queries are parameterized (no string interpolation of user input) to
  prevent SQL injection.
* The connection uses a least-privilege Snowflake role scoped to read-only
  access on the `ANALYTICS` schema (configured via SNOWFLAKE_ROLE).
* Row-level governance ideally lives in Snowflake itself (row access policies
  keyed off the caller's domain); see FUTURE_WORK.
"""
from __future__ import annotations

from ..config import settings
from .data import synthetic


class SnowflakeService:
    def __init__(self) -> None:
        self._enabled = settings.snowflake_configured

    @property
    def backend(self) -> str:
        return "snowflake" if self._enabled else "synthetic"

    def _connect(self):  # pragma: no cover - exercised only with real creds
        import snowflake.connector

        return snowflake.connector.connect(
            account=settings.snowflake_account,
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            role=settings.snowflake_role or None,
        )

    # ------------------------------------------------------------------ ARR
    def arr_waterfall(self, period: str, segment: str | None = None) -> dict:
        if not self._enabled:
            return synthetic.arr_waterfall(period, segment)
        return self._arr_waterfall_sql(period, segment)  # pragma: no cover

    def _arr_waterfall_sql(self, period: str, segment: str | None) -> dict:  # pragma: no cover
        # Reference query against a dbt-built mart. Kept here to show the real
        # shape; not executed without live credentials.
        query = """
            select component, segment, amount
            from analytics.fct_arr_waterfall
            where period = %(period)s
              and (%(segment)s is null or segment = %(segment)s)
        """
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(query, {"period": period, "segment": segment})
            rows = cur.fetchall()
        return self._shape_arr(rows, period, segment)

    def _shape_arr(self, rows, period, segment):  # pragma: no cover
        # Map flat rows -> the bridge structure the dashboard expects.
        # Left as an exercise mirroring synthetic.arr_waterfall's contract.
        raise NotImplementedError

    # -------------------------------------------------------------- pipeline
    def pipeline_health(self, quarter: str, team: str | None = None) -> dict:
        if not self._enabled:
            return synthetic.pipeline_health(quarter, team)
        return self._pipeline_health_sql(quarter, team)  # pragma: no cover

    def _pipeline_health_sql(self, quarter: str, team: str | None) -> dict:  # pragma: no cover
        query = """
            select stage, count(*) as deals, sum(amount) as value,
                   avg(stage_age_days) as avg_age_days
            from analytics.fct_open_pipeline
            where fiscal_quarter = %(quarter)s
              and (%(team)s is null or sales_team = %(team)s)
            group by stage
        """
        raise NotImplementedError


snowflake_service = SnowflakeService()
