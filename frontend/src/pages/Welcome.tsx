import { useAuth } from "../lib/auth";

export default function Welcome() {
  const { me } = useAuth();
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold">Welcome, {me?.name?.split(" ")[0]}</h1>
      <p className="mt-2 text-slate-400">
        This is your governed BI portal. The folders you can see in the left rail
        are scoped to your Okta group memberships.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <InfoCard
          title="Business function folders"
          body="Shared dashboards are visible to everyone. Each domain (Finance, Sales Ops, …) is access-controlled to its members."
        />
        <InfoCard
          title="Your personal workspace"
          body="Draft new dashboards privately, then submit them for domain review and publishing."
        />
        <InfoCard
          title="Claude-powered insight"
          body="Every dashboard pairs a chart with a Claude-generated, data-grounded executive insight panel."
        />
        <InfoCard
          title="Governed publishing"
          body="Reports move Draft → In Review → Published via a domain approver. Nothing reaches a domain folder unreviewed."
        />
      </div>

      <div className="mt-6 card p-4 text-sm text-slate-300">
        <div className="font-medium">Your access</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {me?.is_admin && (
            <span className="badge bg-brand/20 text-brand">Platform Admin</span>
          )}
          {me?.domains.length === 0 && !me?.is_admin && (
            <span className="text-slate-500">
              No domain groups — you can still see Shared dashboards.
            </span>
          )}
          {me?.domains.map((d) => (
            <span key={d.domain} className="badge bg-edge text-slate-300">
              {d.domain_label} · {d.role}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="card p-4">
      <div className="font-medium">{title}</div>
      <div className="mt-1 text-sm text-slate-400">{body}</div>
    </div>
  );
}
