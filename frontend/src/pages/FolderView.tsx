import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Api, ApiError } from "../lib/api";
import { statusColor, statusLabel } from "../lib/format";
import type { Folder, Report } from "../lib/types";

export default function FolderView() {
  const { slug } = useParams();
  const [folder, setFolder] = useState<Folder | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setError(null);
    Api.folders().then((fs) => setFolder(fs.find((f) => f.slug === slug) ?? null));
    Api.folderReports(slug)
      .then(setReports)
      .catch((e: ApiError) =>
        setError(e.status === 404 ? "You don't have access to this folder." : e.message)
      );
  }, [slug]);

  if (error) {
    return (
      <div className="card mx-auto max-w-lg p-6 text-center">
        <div className="text-lg font-medium text-bad">Access denied</div>
        <p className="mt-2 text-sm text-slate-400">{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{folder?.name ?? slug}</h1>
        {folder?.description && (
          <p className="mt-1 text-slate-400">{folder.description}</p>
        )}
      </div>

      {reports.length === 0 ? (
        <div className="card p-6 text-slate-400">No dashboards here yet.</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {reports.map((r) => (
            <Link
              key={r.id}
              to={`/reports/${r.id}`}
              className="card p-5 transition-transform hover:-translate-y-0.5 hover:border-brand/50"
            >
              <div className="flex items-start justify-between">
                <span className="text-xs uppercase tracking-wide text-slate-500">
                  {r.dashboard_type.replace(/_/g, " ")}
                </span>
                <span className={`badge ${statusColor(r.status)}`}>
                  {statusLabel(r.status)}
                </span>
              </div>
              <div className="mt-2 text-lg font-medium">{r.title}</div>
              <div className="mt-3 text-xs text-slate-500">
                Owner {r.owner_email}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
