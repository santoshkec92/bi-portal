import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Api } from "../lib/api";
import type { ApprovalItem } from "../lib/types";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [comments, setComments] = useState<Record<number, string>>({});

  const load = () => Api.approvalQueue().then(setItems);
  useEffect(() => {
    load();
  }, []);

  async function decide(approvalId: number, approve: boolean) {
    await Api.decide(approvalId, approve, comments[approvalId] ?? "");
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Approvals</h1>
      <p className="mt-1 text-slate-400">
        Publish requests awaiting your review. Approving moves the report into
        its Domain Workspace, visible to all members of that function.
      </p>

      <div className="mt-6 space-y-4">
        {items.length === 0 && (
          <div className="card p-6 text-slate-400">
            Nothing in your approval queue.
          </div>
        )}
        {items.map((it) => (
          <div key={it.approval_id} className="card p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-medium">{it.report.title}</span>
                  <span className="badge bg-warn/20 text-warn">In Review</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {it.report.dashboard_type.replace(/_/g, " ")} · requested by{" "}
                  {it.requested_by} · target {it.target_domain}
                </div>
                {it.comment && (
                  <div className="mt-2 text-sm text-slate-400">
                    “{it.comment}”
                  </div>
                )}
              </div>
              <Link to={`/reports/${it.report.id}`} className="btn-ghost">
                Preview
              </Link>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <input
                className="input flex-1"
                placeholder="Review comment (optional)"
                value={comments[it.approval_id] ?? ""}
                onChange={(e) =>
                  setComments((c) => ({ ...c, [it.approval_id]: e.target.value }))
                }
              />
              <button
                onClick={() => decide(it.approval_id, true)}
                className="btn-primary"
              >
                Approve &amp; publish
              </button>
              <button
                onClick={() => decide(it.approval_id, false)}
                className="btn-ghost text-bad"
              >
                Request changes
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
