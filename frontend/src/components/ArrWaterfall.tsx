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

interface BridgeItem {
  label: string;
  value: number;
  kind: "total" | "increase" | "decrease";
}

export default function ArrWaterfall({ data }: { data: any }) {
  const bridge: BridgeItem[] = data.bridge;
  const m = data.metrics;

  // Build floating-bar series: `base` is an invisible offset, `delta` is the
  // visible segment. Totals start at 0; steps float on the running total.
  let running = 0;
  const series = bridge.map((b) => {
    if (b.kind === "total") {
      running = b.value;
      return { ...b, base: 0, delta: b.value };
    }
    const start = running;
    running += b.value;
    return {
      ...b,
      base: Math.min(start, running),
      delta: Math.abs(b.value),
    };
  });

  const color = (k: string) =>
    k === "total" ? "#5b8cff" : k === "increase" ? "#34d399" : "#f87171";

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">ARR Bridge</div>
          <div className="text-xs text-slate-400">
            {data.period} · {data.segment} · {data.currency}
          </div>
        </div>
        <div className="flex gap-4 text-right">
          <Metric label="NRR" value={`${m.nrr_pct}%`} />
          <Metric label="GRR" value={`${m.grr_pct}%`} />
          <Metric label="Net New" value={money(m.net_new_arr)} />
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={series} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            interval={0}
          />
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
            formatter={(_v, _n, p: any) => [money(p.payload.value), p.payload.label]}
          />
          <Bar dataKey="base" stackId="a" fill="transparent" />
          <Bar dataKey="delta" stackId="a" radius={[4, 4, 0, 0]}>
            {series.map((s, i) => (
              <Cell key={i} fill={color(s.kind)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Beginning ARR" value={money(m.beginning_arr)} />
        <Stat label="Ending ARR" value={money(m.ending_arr)} />
        <Stat label="Gross New" value={money(m.gross_new_arr)} good />
        <Stat label="Gross Churn" value={money(m.gross_churn_arr)} bad />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}

function Stat({
  label,
  value,
  good,
  bad,
}: {
  label: string;
  value: string;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <div className="rounded-lg border border-edge p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div
        className={`text-lg font-semibold ${
          good ? "text-good" : bad ? "text-bad" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}
