# RBAC: identity, roles, and enforcement

## 1. From Okta identity to portal permissions

Okta owns **identity** and **group membership**. The portal translates raw group
names into its own concepts — **domains** and **roles** — in exactly one place:
`backend/app/auth/rbac.py`. Nothing downstream ever parses a group string.

```
Okta id_token
  ├─ sub, email, name           → who you are
  └─ groups: ["BI-Finance", …]  → principal_from_claims() → Principal
                                     ├─ domain_roles: {finance: APPROVER, …}
                                     └─ is_admin: bool
```

### Group naming convention

| Okta group | Meaning |
|---|---|
| `BI-Portal-Admin` | platform superuser (all domains, all actions) |
| `BI-Finance` | member (author) of the `finance` domain |
| `BI-Finance-Approver` | approver for `finance` (can approve/reject publishes) |
| `BI-SalesOps` / `BI-SalesOps-Approver` | same for `sales_ops` |
| `BI-RevOps`, `BI-CustomerSuccess` (+ `-Approver`) | RevOps, Customer Success |

The mapping table (`GROUP_TO_DOMAIN`, `ADMIN_GROUP`, `APPROVER_SUFFIX`) is
declarative — rename an Okta group, change one line, no endpoint touched.

### Roles (capability tiers)

| Role | Can do (within a domain) |
|---|---|
| `viewer` | list / open / query **published** reports |
| `author` | + draft reports, request publishing |
| `approver` | + approve / reject publish requests |
| `admin` | everything, every domain (platform-wide) |

> In this prototype, domain membership implies `author`; a `viewer`-only tier is
> modeled and ready (e.g. map a `BI-Finance-Viewer` group) but not seeded.

## 2. The three folder types

| Type | Visible to | Purpose |
|---|---|---|
| **Shared** | every authenticated user | company-wide dashboards |
| **Domain** | members of that domain only | published, governed reports per function |
| **Personal** | the owner only | private drafting area (one per user, auto-created on login) |

## 3. Where enforcement happens

Authorization is enforced **server-side**, in depth. The UI only *hides* things;
the API *forbids* them.

| Layer | File | Responsibility |
|---|---|---|
| Authentication | `auth/dependencies.py` | 401 if no valid session; build `Principal` |
| Identity→perms | `auth/rbac.py` | groups → domains/roles; predicate helpers |
| Resource checks | `services/authz.py` | per-folder / per-report allow/deny |
| Query scoping | `services/authz.py` | list endpoints filter to visible rows |
| Workflow gates | `services/authz.py` | who may submit / approve a publish |
| Audit | `services/provisioning.py` | record logins + (denied) access |

### The key requirement: cross-domain isolation, even by direct URL

A Finance-only user (Frank) attempting a Sales Ops dashboard:

- `GET /api/folders` → Sales Ops folder is **absent** (query-scoped).
- `GET /api/folders/domain-sales_ops/reports` → **404** (point check, no leak).
- `GET /api/dashboards/{id}` for a Sales Ops report → **404** *before any data
  is fetched* from Snowflake/Claude.
- `GET /api/reports/{id}` → **404**.

This is proven in `tests/test_api_rbac.py::test_cross_domain_direct_url_is_404`.

We return **404 (not 403)** for domain resources the caller isn't entitled to,
so the API never confirms the existence of another function's dashboards.

## 4. Why centralize it

Scattering `if "BI-Finance" in groups:` across endpoints is the usual way RBAC
rots: checks drift, some endpoints forget them, and you can't audit the model.
Here, a security reviewer reads two files (`rbac.py`, `authz.py`) to understand
the entire policy, and the policy has unit tests independent of HTTP.

## 5. Defense in depth & deeper governance

- **Two enforcement layers** (point checks + query scoping) so a single bug
  can't leak data.
- **Row-level security at the warehouse**: ideally Snowflake row access policies
  keyed off the caller's domain back-stop the app — even a compromised app role
  can't read another domain's rows. The service connects with a least-privilege
  `BI_PORTAL_READER` role (see `deploy/spcs/setup.sql`).
- **Audit log** (`AuditEvent`) captures logins and denied access for detection.
