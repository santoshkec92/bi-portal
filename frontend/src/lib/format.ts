export function money(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toLocaleString()}`;
}

export function statusColor(status: string): string {
  switch (status) {
    case "published":
      return "bg-good/20 text-good";
    case "in_review":
      return "bg-warn/20 text-warn";
    case "changes_requested":
      return "bg-bad/20 text-bad";
    case "draft":
      return "bg-slate-500/20 text-slate-300";
    default:
      return "bg-slate-500/20 text-slate-300";
  }
}

export const statusLabel = (s: string) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
