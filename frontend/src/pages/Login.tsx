import { useEffect, useState } from "react";
import { Api } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { MockUser } from "../lib/types";

export default function Login() {
  const { refresh } = useAuth();
  const [mode, setMode] = useState<string>("");
  const [users, setUsers] = useState<MockUser[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    Api.authConfig().then((c) => {
      setMode(c.auth_mode);
      if (c.auth_mode === "mock") Api.mockUsers().then(setUsers);
    });
  }, []);

  async function loginMock(key: string) {
    setBusy(key);
    try {
      await Api.mockLogin(key);
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="card w-full max-w-xl p-8">
        <div className="mb-1 text-sm font-medium text-brand">Centralized BI Portal</div>
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-2 text-sm text-slate-400">
          Governed, AI-native dashboards secured by Okta OAuth + RBAC.
        </p>

        {mode === "okta" && (
          <a href="/api/auth/login" className="btn-primary mt-6 w-full">
            Continue with Okta
          </a>
        )}

        {mode === "mock" && (
          <div className="mt-6">
            <div className="mb-3 rounded-lg border border-edge bg-ink/40 p-3 text-xs text-slate-400">
              <span className="font-medium text-warn">Demo (mock) mode.</span> Pick an
              identity to explore RBAC. Each maps to Okta-style groups. Set
              <code className="mx-1 rounded bg-edge px-1">AUTH_MODE=okta</code>
              for the real Authorization Code + PKCE flow.
            </div>
            <div className="grid gap-2">
              {users.map((u) => (
                <button
                  key={u.key}
                  onClick={() => loginMock(u.key)}
                  disabled={busy !== null}
                  className="flex items-center justify-between rounded-lg border border-edge px-4 py-3 text-left hover:bg-edge/40"
                >
                  <div>
                    <div className="font-medium">{u.name}</div>
                    <div className="text-xs text-slate-400">{u.email}</div>
                  </div>
                  <div className="flex flex-wrap justify-end gap-1">
                    {u.groups.length === 0 && (
                      <span className="badge bg-slate-600/30 text-slate-400">
                        no groups
                      </span>
                    )}
                    {u.groups.map((g) => (
                      <span key={g} className="badge bg-brand/20 text-brand">
                        {g}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
