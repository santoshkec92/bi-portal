export type FolderType = "shared" | "domain" | "personal";

export type ReportStatus =
  | "draft"
  | "in_review"
  | "changes_requested"
  | "published"
  | "archived";

export type DashboardType = "arr_waterfall" | "pipeline_health";

export interface DomainRole {
  domain: string;
  domain_label: string;
  role: string;
}

export interface Me {
  sub: string;
  email: string;
  name: string;
  is_admin: boolean;
  groups: string[];
  domains: DomainRole[];
}

export interface Folder {
  id: number;
  name: string;
  slug: string;
  description: string;
  type: FolderType;
  domain: string | null;
  report_count: number;
  can_author: boolean;
}

export interface Report {
  id: number;
  title: string;
  description: string;
  dashboard_type: DashboardType;
  status: ReportStatus;
  folder_id: number;
  owner_email: string;
  target_domain: string | null;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

export interface ApprovalItem {
  approval_id: number;
  target_domain: string;
  requested_by: string;
  comment: string;
  created_at: string;
  report: Report;
}

export interface Insight {
  headline: string;
  narrative: string;
  key_findings: string[];
  risks: string[];
  recommended_actions: string[];
  generated_by: string;
}

export interface Dashboard {
  dashboard_type: DashboardType;
  title: string;
  data: any;
  insight: Insight;
  data_backend: string;
  insight_backend: string;
}

export interface MockUser {
  key: string;
  name: string;
  email: string;
  groups: string[];
}
