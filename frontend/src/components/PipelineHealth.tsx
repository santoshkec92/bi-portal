import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { money } from "../lib/format";

export default function PipelineHealth({ data }: { data: any }) {
  const m = data.metrics;
  const funnel = data.funnel;
  const aging = data.aging;
  const coverageHealthy = m.coverage_ratio >= 3;

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold">Pipeline by Stage</div>
            <div className="text-xs text-slate-400">
              {data.quarter} · {data.team} · {data.currency}
            </div>
          </div>
          <div className="flex gap-4 text-right">
            <Metric
              label="Coverage"
              value={`${m.coverage_ratio}x`}
              tone={coverageHealthy ? "text-good" : "text-warn"}
            />
            <Metric label="Weighted" value={money(m.weighted_pipeline)} />
            <Metric label="Quota" value={money(m.quota)} />
          </div>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={funnel} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            <XAxis dataKey="stage" tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
            <YAxis
              tickFormatter={(v) => money(v)}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: "#111a2e",
                border: "1px solid #1e2a44",
                borderRadius: 8,
              }}
              formatter={(v: any, _n, p: any) => [
                `${money(v)} · ${p.payload.deals} deals · ${p.payload.win_rate_pct}% win`,
                p.payload.stage,
              ]}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="#5b8cff" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card p-5">
        <div className="mb-3 text-lg font-semibold">Deal Aging</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={aging}
            layout="vertical"
            margin={{ top: 0, right: 20, left: 40, bottom: 0 }}
          >
            <XAxis
              type="number"
              tickFormatter={(v) => money(v)}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
            />
            <YAxis
              type="category"
              dataKey="bucket"
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              width={140}
            />
            <Tooltip
              contentStyle={{
                background: "#111a2e",
                border: "1px solid #1e2a44",
                borderRadius: 8,
              }}
              formatter={(v: any, _n, p: any) => [
                `${money(v)} · ${p.payload.deals} deals`,
                p.payload.bucket,
              ]}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {aging.map((a: any, i: number) => (
                <Cell
                  key={i}
                  fill={a.bucket.includes("at risk") ? "#f87171" : "#5b8cff"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Stat label="Open Pipeline" value={money(m.open_pipeline)} />
          <Stat label="At Risk (90+d)" value={money(m.at_risk_value)} bad />
          <Stat
            label="Slipped"
            value={`${money(m.slipped_value)} · ${m.slipped_count}`}
            bad
          />
        </div>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`font-semibold ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

function Stat({
  label,
  value,
  bad,
}: {
  label: string;
  value: string;
  bad?: boolean;
}) {
  return (
    <div className="rounded-lg border border-edge p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-lg font-semibold ${bad ? "text-bad" : ""}`}>{value}</div>
    </div>
  );
}
