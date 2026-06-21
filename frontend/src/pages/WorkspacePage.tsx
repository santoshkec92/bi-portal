import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { statusColor, statusLabel } from "../lib/format";
import type { DashboardType, Report } from "../lib/types";

export default function WorkspacePage() {
  const { me } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [creating, setCreating] = useState(false);

  const authorable = me?.is_admin
    ? [
        { domain: "finance", domain_label: "Finance", role: "admin" },
        { domain: "sales_ops", domain_label: "Sales Ops", role: "admin" },
        { domain: "revops", domain_label: "RevOps", role: "admin" },
        { domain: "customer_success", domain_label: "Customer Success", role: "admin" },
      ]
    : me?.domains ?? [];

  const load = () => Api.myReports().then(setReports);
  useEffect(() => {
    load();
  }, []);

  async function submit(id: number) {
    await Api.submitReport(id, "Submitting for domain review.");
    load();
  }
  async function remove(id: number) {
    await Api.deleteReport(id);
    load();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">My Workspace</h1>
          <p className="mt-1 text-slate-400">
            Private drafting area. Create a dashboard, then submit it for domain
            review to publish.
          </p>
        </div>
        {authorable.length > 0 && (
          <button onClick={() => setCreating((v) => !v)} className="btn-primary">
            {creating ? "Close" : "+ New dashboard"}
          </button>
        )}
      </div>

      {creating && (
        <NewReportForm
          authorable={authorable}
          onCreated={() => {
            setCreating(false);
            load();
          }}
        />
      )}

      {authorable.length === 0 && (
        <div className="card mb-4 p-4 text-sm text-slate-400">
          You aren't a member of any business function, so you can't author
          dashboards. Ask an admin to add you to an Okta group (e.g. BI-Finance).
        </div>
      )}

      <div className="space-y-3">
        {reports.length === 0 && (
          <div className="card p-6 text-slate-400">No reports yet.</div>
        )}
        {reports.map((r) => (
          <div key={r.id} className="card flex items-center justify-between p-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{r.title}</span>
                <span className={`badge ${statusColor(r.status)}`}>
                  {statusLabel(r.status)}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {r.dashboard_type.replace(/_/g, " ")} → {r.target_domain}
              </div>
            </div>
            <div className="flex gap-2">
              <Link to={`/reports/${r.id}`} className="btn-ghost">
                View
              </Link>
              {(r.status === "draft" || r.status === "changes_requested") && (
                <button onClick={() => submit(r.id)} className="btn-primary">
                  Submit for review
                </button>
              )}
              {r.status === "draft" && (
                <button
                  onClick={() => remove(r.id)}
                  className="btn-ghost text-bad"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function NewReportForm({
  authorable,
  onCreated,
}: {
  authorable: { domain: string; domain_label: string }[];
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<DashboardType>("arr_waterfall");
  const [domain, setDomain] = useState(authorable[0]?.domain ?? "");
  const [period, setPeriod] = useState("FY26-Q1");
  const [segment, setSegment] = useState("");
  const [busy, setBusy] = useState(false);

  async function create() {
    setBusy(true);
    const config =
      type === "arr_waterfall"
        ? { period, segment: segment || null }
        : { quarter: period, team: segment || null };
    try {
      await Api.createReport({
        title: title || "Untitled dashboard",
        dashboard_type: type,
        target_domain: domain,
        config,
      });
      onCreated();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card mb-6 grid gap-3 p-5 sm:grid-cols-2">
      <Field label="Title">
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Enterprise ARR deep-dive"
        />
      </Field>
      <Field label="Dashboard type">
        <select
          className="input"
          value={type}
          onChange={(e) => setType(e.target.value as DashboardType)}
        >
          <option value="arr_waterfall">ARR Waterfall</option>
          <option value="pipeline_health">Pipeline Health</option>
        </select>
      </Field>
      <Field label="Target domain (publish destination)">
        <select
          className="input"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
        >
          {authorable.map((d) => (
            <option key={d.domain} value={d.domain}>
              {d.domain_label}
            </option>
          ))}
        </select>
      </Field>
      <Field label={type === "arr_waterfall" ? "Period" : "Quarter"}>
        <input
          className="input"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
        />
      </Field>
      <Field label={type === "arr_waterfall" ? "Segment (optional)" : "Team (optional)"}>
        <input
          className="input"
          value={segment}
          onChange={(e) => setSegment(e.target.value)}
          placeholder={type === "arr_waterfall" ? "Enterprise / Mid-Market / SMB" : "Team name"}
        />
      </Field>
      <div className="flex items-end">
        <button onClick={create} disabled={busy} className="btn-primary w-full">
          {busy ? "Creating…" : "Create draft"}
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-slate-400">{label}</span>
      {children}
    </label>
  );
}
