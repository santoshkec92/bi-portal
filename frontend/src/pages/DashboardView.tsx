import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ArrWaterfall from "../components/ArrWaterfall";
import PipelineHealth from "../components/PipelineHealth";
import InsightPanel from "../components/InsightPanel";
import { Api, ApiError } from "../lib/api";
import type { Dashboard } from "../lib/types";

export default function DashboardView() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    setDash(null);
    setError(null);
    Api.dashboard(Number(reportId))
      .then(setDash)
      .catch((e: ApiError) =>
        setError(
          e.status === 404
            ? "This dashboard doesn't exist or you don't have access to it."
            : e.message
        )
      );
  }, [reportId]);

  if (error) {
    return (
      <div className="card mx-auto max-w-lg p-6 text-center">
        <div className="text-lg font-medium text-bad">Not available</div>
        <p className="mt-2 text-sm text-slate-400">{error}</p>
        <button onClick={() => navigate(-1)} className="btn-ghost mt-4">
          Go back
        </button>
      </div>
    );
  }

  if (!dash) {
    return <div className="text-slate-400">Loading dashboard…</div>;
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{dash.title}</h1>
          <div className="mt-1 text-xs text-slate-500">
            Data: {dash.data_backend} · Insight: {dash.insight_backend}
          </div>
        </div>
        <button onClick={() => navigate(-1)} className="btn-ghost">
          ← Back
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {dash.dashboard_type === "arr_waterfall" ? (
            <ArrWaterfall data={dash.data} />
          ) : (
            <PipelineHealth data={dash.data} />
          )}
        </div>
        <div className="lg:col-span-1">
          <InsightPanel insight={dash.insight} backend={dash.insight_backend} />
        </div>
      </div>
    </div>
  );
}
