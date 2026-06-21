import type {
  ApprovalItem,
  Dashboard,
  Folder,
  Me,
  MockUser,
  Report,
} from "./types";

// Single typed wrapper around fetch. `credentials: include` ensures the signed
// session cookie travels on every request.
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const Api = {
  authConfig: () => api<{ auth_mode: string; app_name: string }>("/api/auth/config"),
  mockUsers: () => api<MockUser[]>("/api/auth/mock-users"),
  mockLogin: (user: string) =>
    api<{ ok: boolean }>(`/api/auth/mock-login?user=${user}`, { method: "POST" }),
  logout: () => api<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  me: () => api<Me>("/api/me"),
  folders: () => api<Folder[]>("/api/folders"),
  folderReports: (slug: string) =>
    api<Report[]>(`/api/folders/${slug}/reports`),

  myReports: () => api<Report[]>("/api/reports/mine"),
  createReport: (body: unknown) =>
    api<Report>("/api/reports", { method: "POST", body: JSON.stringify(body) }),
  submitReport: (id: number, comment: string) =>
    api<Report>(`/api/reports/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  deleteReport: (id: number) =>
    api<void>(`/api/reports/${id}`, { method: "DELETE" }),
  approvalQueue: () => api<ApprovalItem[]>("/api/reports/approvals/queue"),
  decide: (approvalId: number, approve: boolean, comment: string) =>
    api<Report>(`/api/reports/approvals/${approvalId}/decide`, {
      method: "POST",
      body: JSON.stringify({ approve, comment }),
    }),

  dashboard: (reportId: number) =>
    api<Dashboard>(`/api/dashboards/${reportId}`),
  preview: (body: unknown) =>
    api<Dashboard>("/api/dashboards/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
