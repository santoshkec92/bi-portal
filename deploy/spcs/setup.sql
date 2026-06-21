-- ===========================================================================
-- Snowflake Container Services (SPCS) deployment for the BI Portal.
-- Run as ACCOUNTADMIN (or a role with the equivalent grants).
-- ===========================================================================

-- 1. Database, schema, image repository, compute pool ----------------------
CREATE DATABASE IF NOT EXISTS bi_portal_db;
CREATE SCHEMA IF NOT EXISTS bi_portal_db.public;
CREATE IMAGE REPOSITORY IF NOT EXISTS bi_portal_db.public.bi_portal_repo;

CREATE COMPUTE POOL IF NOT EXISTS bi_portal_pool
  MIN_NODES = 1
  MAX_NODES = 2
  INSTANCE_FAMILY = CPU_X64_XS;

-- 2. Least-privilege role the service uses to read analytics ----------------
CREATE ROLE IF NOT EXISTS bi_portal_reader;
GRANT USAGE ON DATABASE prod TO ROLE bi_portal_reader;
GRANT USAGE ON SCHEMA prod.analytics TO ROLE bi_portal_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA prod.analytics TO ROLE bi_portal_reader;
GRANT SELECT ON FUTURE TABLES IN SCHEMA prod.analytics TO ROLE bi_portal_reader;
GRANT USAGE ON WAREHOUSE bi_wh TO ROLE bi_portal_reader;

-- 3. Secrets (native secret management). Values set out-of-band, never in git.
CREATE SECRET IF NOT EXISTS bi_portal_db.public.session_secret
  TYPE = GENERIC_STRING SECRET_STRING = '<32+ random bytes>';
CREATE SECRET IF NOT EXISTS bi_portal_db.public.okta_issuer
  TYPE = GENERIC_STRING SECRET_STRING = 'https://your-tenant.okta.com/oauth2/default';
CREATE SECRET IF NOT EXISTS bi_portal_db.public.okta_client_id
  TYPE = GENERIC_STRING SECRET_STRING = '0oaXXXXXXXX';
CREATE SECRET IF NOT EXISTS bi_portal_db.public.okta_client_secret
  TYPE = GENERIC_STRING SECRET_STRING = '<okta-client-secret>';
CREATE SECRET IF NOT EXISTS bi_portal_db.public.anthropic_api_key
  TYPE = GENERIC_STRING SECRET_STRING = 'sk-ant-XXXX';
CREATE SECRET IF NOT EXISTS bi_portal_db.public.database_url
  TYPE = GENERIC_STRING SECRET_STRING = 'postgresql+psycopg2://bi:pw@host:5432/bi_portal';

-- 4. Egress to Okta + Anthropic (external access integration) ---------------
CREATE OR REPLACE NETWORK RULE bi_portal_egress
  MODE = EGRESS TYPE = HOST_PORT
  VALUE_LIST = ('api.anthropic.com', 'your-tenant.okta.com');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION bi_portal_eai
  ALLOWED_NETWORK_RULES = (bi_portal_egress)
  ALLOWED_AUTHENTICATION_SECRETS = (
    bi_portal_db.public.anthropic_api_key,
    bi_portal_db.public.okta_client_secret
  )
  ENABLED = TRUE;

-- 5. Push the image, then create the service --------------------------------
-- (CLI) docker login <account>.registry.snowflakecomputing.com -u <user>
--       docker tag bi-portal:1.0.0 \
--         <account>.registry.snowflakecomputing.com/bi_portal_db/public/bi_portal_repo/bi-portal:1.0.0
--       docker push ...

CREATE SERVICE IF NOT EXISTS bi_portal_db.public.bi_portal_svc
  IN COMPUTE POOL bi_portal_pool
  FROM SPECIFICATION_FILE = 'service-spec.yaml'
  EXTERNAL_ACCESS_INTEGRATIONS = (bi_portal_eai);

-- 6. Inspect ----------------------------------------------------------------
-- SHOW SERVICES IN SCHEMA bi_portal_db.public;
-- SELECT SYSTEM$GET_SERVICE_STATUS('bi_portal_db.public.bi_portal_svc');
-- SHOW ENDPOINTS IN SERVICE bi_portal_db.public.bi_portal_svc;  -- public URL
