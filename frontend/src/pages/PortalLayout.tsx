import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Folder } from "../lib/types";

const FOLDER_ICON: Record<string, string> = {
  shared: "🌐",
  domain: "🏢",
  personal: "👤",
};

export default function PortalLayout() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const [folders, setFolders] = useState<Folder[]>([]);

  useEffect(() => {
    Api.folders().then(setFolders);
  }, []);

  const grouped = {
    shared: folders.filter((f) => f.type === "shared"),
    domain: folders.filter((f) => f.type === "domain"),
    personal: folders.filter((f) => f.type === "personal"),
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2 text-sm ${
      isActive ? "bg-brand/20 text-brand" : "text-slate-300 hover:bg-edge/40"
    }`;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-72 flex-col border-r border-edge bg-ink/60 p-4">
        <button
          onClick={() => navigate("/")}
          className="mb-6 text-left text-lg font-semibold text-white"
        >
          <span className="text-brand">●</span> BI Portal
        </button>

        <nav className="flex-1 space-y-5 overflow-y-auto">
          <Section title="Workspace">
            <NavLink to="/workspace" className={navClass}>
              👤 My Workspace
            </NavLink>
            {me?.domains.some((d) => d.role === "approver") || me?.is_admin ? (
              <NavLink to="/approvals" className={navClass}>
                ✅ Approvals
              </NavLink>
            ) : null}
          </Section>

          {(["shared", "domain", "personal"] as const).map((kind) =>
            grouped[kind].length ? (
              <Section
                key={kind}
                title={
                  kind === "shared"
                    ? "Shared"
                    : kind === "domain"
                    ? "Business Functions"
                    : "Personal"
                }
              >
                {grouped[kind].map((f) => (
                  <NavLink key={f.id} to={`/folders/${f.slug}`} className={navClass}>
                    <span className="mr-1">{FOLDER_ICON[f.type]}</span>
                    {f.name}
                    <span className="ml-2 text-xs text-slate-500">
                      {f.report_count}
                    </span>
                  </NavLink>
                ))}
              </Section>
            ) : null
          )}
        </nav>

        {/* User card */}
        <div className="mt-4 rounded-lg border border-edge p-3">
          <div className="text-sm font-medium">{me?.name}</div>
          <div className="text-xs text-slate-400">{me?.email}</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {me?.is_admin && (
              <span className="badge bg-brand/20 text-brand">admin</span>
            )}
            {me?.domains.map((d) => (
              <span key={d.domain} className="badge bg-edge text-slate-300">
                {d.domain_label}:{d.role}
              </span>
            ))}
          </div>
          <button onClick={logout} className="btn-ghost mt-3 w-full">
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}
