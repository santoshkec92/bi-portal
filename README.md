# Centralized BI Portal

A secure, self-serve home for company dashboards — where every team gets its own
private set of reports, the right people (and only the right people) can see them,
and an AI assistant explains what each chart actually *means* for the business.

> Built for the "BI Portal with Claude Dashboards" assignment. It runs end-to-end
> on a laptop with **no external accounts or API keys required** — the login,
> security, data, and AI all have built-in stand-ins so you can try the whole
> thing immediately.

---

## The 30-second version

Most companies have data, but getting to it is painful:

- Business teams (Finance, Sales, etc.) can't easily get the numbers they need, so
  they file a request and **wait days** for the data team to pull it.
- The data team **drowns in repetitive requests** instead of doing higher-value work.
- The workarounds — emailed spreadsheets, one-off exports — are **insecure and
  untrustworthy** (no one knows which version is right, or who can see it).

This portal fixes that. It gives each business function a **self-serve folder of
dashboards** they can open themselves, locked down so people only see what they're
allowed to. And next to every chart, **Claude (an AI model from Anthropic) writes a
short, plain-language briefing** — the key takeaway, the risks, and what to do next.

**The result:** faster decisions for the business, fewer tickets for the data team,
and security/governance you can actually trust.

---

## How it works, in plain English

Think of it like **Google Drive, but for dashboards, with a security guard and a
built-in analyst.**

1. **Folders = who can see what.** There are three kinds of folders:
   - **Shared** — company-wide dashboards everyone can see.
   - **Domain** — one per business function (Finance, Sales Ops, …); only members
     of that function can open it.
   - **Personal** — your own private space to build drafts before anyone else sees them.

2. **A security guard at the door.** When you log in (via your company's standard
   single-sign-on), the portal checks which groups you belong to and shows you only
   the folders you're entitled to. If you try to open another team's dashboard by
   guessing its link, the portal acts as if it doesn't even exist.

3. **A review step before anything goes "live."** You draft a dashboard privately,
   then submit it. A designated approver for that function reviews and publishes it.
   Nothing reaches a team's official folder without that sign-off — and every
   submission and approval is logged.

4. **An AI analyst on every chart.** The chart shows *what* happened; Claude adds a
   short brief explaining *why it matters and what to do* — grounded strictly in the
   numbers on screen, never made up.

---

## What you'll see in the demo

The app ships with seven sample users so you can experience the security model
firsthand (no setup needed). For example:

1. Log in as **Frank** (a Finance analyst). You'll see the **Finance** and **Shared**
   folders — but **not** Sales Ops.
2. Open the **ARR Waterfall** dashboard: a revenue chart on the left, an AI-written
   insight on the right.
3. Try to open a **Sales Ops** dashboard by pasting its direct link → you get a
   **"not found"** page. The data is genuinely protected, not just hidden.
4. As Frank, draft a new report in your **Personal** workspace and submit it for review.
5. Log in as **Fiona** (a Finance approver) → go to **Approvals** → approve Frank's
   report → it now appears in the Finance folder for the whole team.

| User | Belongs to | Can see |
|---|---|---|
| Fiona | Finance (+ approver) | Finance (and can approve), Shared |
| Frank | Finance | Finance, Shared (can draft, can't approve) |
| Sam | Sales Ops (+ approver) | Sales Ops (and can approve), Shared |
| Rita | RevOps | RevOps, Shared |
| Casey | Customer Success | Customer Success, Shared |
| Ada | Platform Admin | Everything |
| Nina | _(no groups)_ | Shared only |

---

## Plain-English glossary

This project touches a few enterprise tools. Here's what each is, in one line:

| Term | What it means here |
|---|---|
| **Dashboard / Report** | A page with a chart (and now an AI insight) about the business. |
| **Okta** | The company's single-sign-on — the system that proves who you are when you log in. |
| **RBAC** (Role-Based Access Control) | The rule book for "who can see and do what," based on the groups you belong to. |
| **Snowflake** | The company's central data warehouse where the analytical numbers live. |
| **Claude** | The AI model (from Anthropic) that writes the plain-language insight next to each chart. |
| **Domain** | A business function — Finance, Sales Ops, RevOps, Customer Success. |
| **Approver** | A person allowed to review and publish reports for their function. |
| **ARR** | Annual Recurring Revenue — the headline subscription-revenue metric Finance tracks. |
| **Pipeline** | The set of in-progress sales deals Sales Ops forecasts from. |

---

## Why this is built well (for the engineers in the room)

| Capability | How it's done | Where |
|---|---|---|
| Folder shell: **Shared / Domain / Personal** workspaces | SQLAlchemy data model + React layout | `backend/app/models.py`, `frontend/.../PortalLayout.tsx` |
| **Okta OAuth2 Authorization Code + PKCE** (with a mock fallback for demos) | Standards-based login, no passwords stored | `backend/app/auth/okta.py`, `auth.py` router |
| **RBAC** enforced server-side, in one place | Okta group → domain/role, checked at folder + dashboard level | `backend/app/auth/rbac.py`, `services/authz.py` |
| Governed **publishing workflow** (Draft → Review → Published) | Explicit, audited state machine | `backend/app/api/routers/reports.py` |
| Two **Claude dashboards**: ARR Waterfall + Pipeline Health | Structured data → chart + grounded AI brief | `services/claude_service.py`, `api/routers/dashboards.py` |
| **Deployable** as one container | Docker → Kubernetes or Snowflake Container Services | `deploy/` |

Three design choices worth calling out:

- **Security is centralized and tested.** All "who can do what" logic lives in two
  files, not scattered across the app, and has unit tests independent of the web layer.
- **It degrades gracefully.** No Okta, Claude, or Snowflake credentials? The app
  still runs with a mock login, AI stand-in, and synthetic data — **the exact same
  code paths**, so the demo behaves like production minus the live integrations.
- **It ships as a single artifact.** One container serves both the API and the web
  app, which removes a whole class of deployment and cross-origin headaches.

Full diagrams, the security model, AI prompt design, and roadmap are in
[`docs/`](docs/):
[ARCHITECTURE](docs/ARCHITECTURE.md) ·
[RBAC](docs/RBAC.md) ·
[PROMPTS](docs/PROMPTS.md) ·
[FUTURE_WORK](docs/FUTURE_WORK.md).

---

## Architecture at a glance

```
                         ┌──────────────────────────────────────────┐
   Browser (web app)     │            Single container                │
   React + charts  ─────▶│  FastAPI (the backend)                     │
                         │   ├─ /api/auth  Okta login ───────────────▶│──▶ Okta (proves identity)
                         │   ├─ RBAC (turns identity into permissions)│
                         │   ├─ /api/folders /reports  (access checks)│
   served to the    ◀────│   ├─ /api/dashboards ──┐                   │
   browser by FastAPI    │   │                     ├─ Snowflake svc ──▶│──▶ Snowflake (the data)
                         │   │                     └─ Claude svc ─────▶│──▶ Anthropic (the AI insight)
                         │   └─ SQLAlchemy (who-owns-what metadata) ──▶│──▶ Postgres / SQLite
                         └──────────────────────────────────────────┘
```

- **One origin in production**: the backend serves the web app, so logins are simple
  and there's no cross-origin configuration to manage.
- **Stateless sessions** (a signed cookie holds your identity) → the app can scale to
  many copies with no shared session database.
- **Pluggable backends**: production and demo run identical code; they differ only by
  which environment variables are set.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full diagrams and data model.

---

## Running the app

> No accounts, API keys, or external services needed.
> Everything runs locally in demo mode out of the box.

---

### Option A — Docker (recommended)

**Requires:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

**Step 1** — Clone the repo and enter the folder:
```bash
git clone https://github.com/santoshkec92/bi-portal.git
cd bi-portal
```

**Step 2** — Start the app (one command builds and runs everything):
```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

This takes 2–3 minutes the first time (downloading dependencies). You'll see logs scrolling.
Wait until you see a line like:
```
portal_1  | INFO:     Application startup complete.
```

**Step 3** — Open your browser and go to:
```
http://localhost:8000
```

You'll see the **Sign in** screen with seven demo users. Click any name to log in — no password needed.

**To stop:** press `Ctrl+C` in the terminal, then run `docker compose -f deploy/docker/docker-compose.yml down`.

---

### Option B — Without Docker (two terminals)

**Requires:**
- Python 3.11 or newer — check with `python3 --version`
- Node 20 or newer — check with `node --version`

**Step 1** — Clone the repo:
```bash
git clone https://github.com/santoshkec92/bi-portal.git
cd bi-portal
```

**Step 2** — Open **Terminal 1** and start the backend:
```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Wait until you see:
```
INFO:     Application startup complete.
```
**Keep this terminal open and running.**

**Step 3** — Open a **second terminal** (keep Terminal 1 running) and start the frontend:
```bash
cd bi-portal/frontend         # from the repo root
npm install
npm run dev
```

Wait until you see:
```
VITE ready in ...ms
➜  Local:   http://localhost:5173/
```

**Step 4** — Open your browser and go to:
```
http://localhost:5173
```

You'll see the **Sign in** screen with seven demo users. Click any name to log in.

---

### Logging in

No passwords — just click a name on the Sign in screen:

| Click this user | To see |
|---|---|
| **Fiona** | Finance dashboards + the Approvals queue |
| **Frank** | Finance dashboards only (no approval rights) |
| **Sam** | Sales Ops dashboards + Approvals |
| **Rita** | RevOps dashboards |
| **Casey** | Customer Success dashboards |
| **Ada** | Everything (platform admin) |
| **Nina** | Shared dashboards only (no domain access) |

**To try the security model:** log in as Frank, then try opening a Sales Ops dashboard
by direct URL — you'll get a "not found" page. The data is genuinely blocked server-side,
not just hidden in the UI.

---

### Troubleshooting

**Sign in screen is blank (no user buttons showing)**
→ The backend is not running. Check Terminal 1 — it must show "Application startup complete."
Make sure you started the backend before opening the browser.

**`npm run dev` errors or frontend won't start**
→ Make sure `npm install` ran first and completed without errors.

**`pip install` fails**
→ Check your Python version: `python3 --version`. Needs 3.11 or newer.
On a Mac with the default system Python (3.9), use `python3.11` or `python3.13` explicitly.

**Port already in use**
→ Something else is on port 8000 or 5173. Stop it, or kill it:
```bash
lsof -ti:8000 | xargs kill   # free port 8000
lsof -ti:5173 | xargs kill   # free port 5173
```

**After stopping and restarting, data is reset**
→ Normal for Option B (SQLite reseeds on startup). Use Docker for a persistent database.

---

## Switch on the real integrations

Everything is controlled by environment variables (all documented in
[`.env.example`](.env.example)). Demo mode needs none of these; flip them on to go live:

```bash
AUTH_MODE=okta                  # use real single-sign-on instead of the demo logins
OKTA_ISSUER=https://your-tenant.okta.com/oauth2/default
OKTA_CLIENT_ID=...
OKTA_CLIENT_SECRET=...           # optional for public PKCE clients
ANTHROPIC_API_KEY=sk-ant-...     # turns on real Claude insights (otherwise a built-in stand-in)
SNOWFLAKE_ACCOUNT=...            # turns on real warehouse data (otherwise synthetic data)
```

- **Okta**: create an OIDC app, point its redirect to `${BASE_URL}/api/auth/callback`,
  and add a "groups" claim. Group naming is documented in [docs/RBAC.md](docs/RBAC.md).
- **Claude**: set `ANTHROPIC_API_KEY`; without it, insights come from a deterministic
  stand-in that's clearly labeled in the UI.
- **Snowflake**: set the `SNOWFLAKE_*` values; without them, dashboards use built-in
  synthetic data of the same shape. Reference SQL is in `services/snowflake_service.py`.

---

## Deploy

- **Kubernetes**: `deploy/k8s/` — Namespace, ConfigMap, example Secret, Deployment
  (with health probes, non-root, read-only filesystem), Service, and TLS Ingress.
  ```bash
  kubectl apply -f deploy/k8s/namespace.yaml
  kubectl apply -f deploy/k8s/configmap.yaml
  kubectl apply -f deploy/k8s/secret.example.yaml   # replace with real secrets first
  kubectl apply -f deploy/k8s/deployment.yaml -f deploy/k8s/service.yaml -f deploy/k8s/ingress.yaml
  ```
- **Snowflake Container Services**: `deploy/spcs/setup.sql` + `service-spec.yaml`
  (compute pool, image repo, least-privilege reader role, native secret objects,
  external-access integration for Okta + Anthropic, and `CREATE SERVICE`).

Secrets are always injected by the platform's secret manager — never baked into the
image. Rotating a secret is a restart, not a code change.

---

## Tests

```bash
cd backend && . .venv/bin/activate && pytest -q
```

- `tests/test_rbac.py` — checks the "group → permission" rules in isolation.
- `tests/test_api_rbac.py` — proves end-to-end that one team **cannot** see another
  team's dashboards (by list *or* by direct link), and that only approvers see the
  approval queue.

---

## Repository layout

```
bi-portal/
├── backend/                # FastAPI app (the server + API)
│   └── app/
│       ├── auth/           # login (Okta + demo), sessions, the RBAC rule book
│       ├── api/routers/    # the API endpoints: auth, me, folders, reports, dashboards
│       ├── services/       # access checks, Snowflake, Claude, user setup, synthetic data
│       ├── models.py       # the data model (users, folders, reports, approvals, audit)
│       ├── schemas.py      # the API's input/output shapes
│       ├── seed.py         # creates the sample folders + demo content on first run
│       └── main.py         # wires it all together (and serves the web app)
├── frontend/               # React web app (the user interface)
├── deploy/                 # how to ship it: docker / kubernetes / snowflake
└── docs/                   # architecture, security, AI prompt design, roadmap, slides
```
