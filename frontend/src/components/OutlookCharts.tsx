import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Consensus } from "../model/consensus";
import { FOSSIL_HISTORY } from "../model/history";
import type { TimelinePoint } from "../model/timeline";
import { ChartCard } from "./ChartCard";
import { ChartTooltip } from "./ChartTooltip";

const AXIS = { stroke: "var(--axis)", tick: { fill: "var(--text-muted)", fontSize: 12 } } as const;
const GRID = { stroke: "var(--grid)", strokeWidth: 1, vertical: false } as const;
const CURSOR_LINE = { stroke: "var(--axis)", strokeWidth: 1 } as const;
const CURSOR_FILL = { fill: "var(--hover-wash)" } as const;

const fmt0 = (n: number) => n.toFixed(0);
const fmt1 = (n: number) => n.toFixed(1);

export function HistoryChart({ consensus, dim }: { consensus: Consensus; dim?: boolean }) {
  const data = FOSSIL_HISTORY.map((p) => ({ year: p.year, twh: p.twh / 1000 }));
  return (
    <ChartCard
      title="Global fossil fuel consumption and the consensus peak"
      subtitle={`1900–2024 actuals (thousand TWh/yr); shaded p10–p90 window ${fmt0(consensus.p10)}–${fmt0(consensus.p90)}, median ${fmt0(consensus.median)}`}
      dim={dim}
      columns={[
        { key: "year", label: "Year" },
        { key: "twh", label: "Fossil energy (thousand TWh)", numeric: true },
      ]}
      rows={data.filter((d) => d.year % 5 === 0 || d.year >= 2019).map((d) => ({ year: d.year, twh: fmt1(d.twh) }))}
    >
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 16, right: 24, bottom: 4, left: 0 }}>
          <CartesianGrid {...GRID} />
          <XAxis
            dataKey="year"
            type="number"
            domain={[1900, 2060]}
            ticks={[1900, 1920, 1940, 1960, 1980, 2000, 2020, 2040, 2060]}
            allowDataOverflow
            {...AXIS}
          />
          <YAxis {...AXIS} width={36} tickFormatter={fmt0} />
          <Tooltip
            cursor={CURSOR_LINE}
            content={<ChartTooltip title={(l) => `${l}`} format={(v) => `${fmt1(Number(v))}K TWh`} />}
          />
          <ReferenceArea
            x1={consensus.p10}
            x2={consensus.p90}
            fill="var(--series-2)"
            fillOpacity={0.12}
            stroke="none"
          />
          <ReferenceLine
            x={consensus.median}
            stroke="var(--series-2)"
            strokeWidth={2}
            label={{
              value: `consensus peak ${fmt0(consensus.median)}`,
              position: "insideTopLeft",
              fill: "var(--text-secondary)",
              fontSize: 12,
            }}
          />
          <Area
            dataKey="twh"
            name="Fossil energy"
            stroke="var(--series-1)"
            strokeWidth={2}
            fill="var(--series-1)"
            fillOpacity={0.1}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)" }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function DistributionChart({ consensus, dim }: { consensus: Consensus; dim?: boolean }) {
  const data = consensus.histogram;
  return (
    <ChartCard
      title="Where the peak year lands"
      subtitle={`Probability by year from ${consensus.draws.toLocaleString()} weighted draws · P(≤2030) ${(consensus.pBy2030 * 100).toFixed(0)}%`}
      dim={dim}
      columns={[
        { key: "year", label: "Year" },
        { key: "p", label: "Probability", numeric: true },
      ]}
      rows={data.filter((d) => d.p > 0.001).map((d) => ({ year: d.year, p: `${(d.p * 100).toFixed(1)}%` }))}
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 0 }} barCategoryGap={2}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="year" ticks={[2020, 2030, 2040, 2050, 2060]} {...AXIS} />
          <YAxis {...AXIS} width={40} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
          <Tooltip
            cursor={CURSOR_FILL}
            content={<ChartTooltip title={(l) => `${l}`} format={(v) => `${(Number(v) * 100).toFixed(1)}%`} />}
          />
          <ReferenceLine x={consensus.median} stroke="var(--series-2)" strokeWidth={2} />
          <Bar
            dataKey="p"
            name="Probability"
            fill="var(--series-1)"
            maxBarSize={24}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function TimelineChart({ points, dim }: { points: TimelinePoint[]; dim?: boolean }) {
  const last = points.length - 1;
  // Direct-label only the endpoint of each line; the legend + tooltip carry the rest.
  const endLabel = (props: { x?: number; y?: number; index?: number; value?: number }) =>
    props.index === last && props.value !== undefined ? (
      <text x={(props.x ?? 0) + 8} y={(props.y ?? 0) + 4} fill="var(--text-secondary)" fontSize={12}>
        {fmt1(props.value)}
      </text>
    ) : (
      <g />
    );
  return (
    <ChartCard
      title="Consensus over time"
      subtitle="Median peak year each week as kept articles accumulated (registry only vs. with the media nowcast)"
      dim={dim}
      columns={[
        { key: "label", label: "Week of" },
        { key: "articlesSeen", label: "Articles seen", numeric: true },
        { key: "claims", label: "Peak claims", numeric: true },
        { key: "registryOnly", label: "Registry only", numeric: true },
        { key: "withNowcast", label: "With nowcast", numeric: true },
      ]}
      rows={points.map((p) => ({
        label: p.label,
        articlesSeen: p.articlesSeen,
        claims: p.claims,
        registryOnly: fmt1(p.registryOnly),
        withNowcast: fmt1(p.withNowcast),
      }))}
    >
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={points} margin={{ top: 12, right: 60, bottom: 4, left: 0 }}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="label" {...AXIS} />
          <YAxis {...AXIS} width={40} domain={["dataMin - 1", "dataMax + 1"]} tickFormatter={fmt0} />
          <Tooltip
            cursor={CURSOR_LINE}
            content={<ChartTooltip title={(l) => `Week of ${l}`} format={(v) => fmt1(Number(v))} />}
          />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
          <Line
            dataKey="registryOnly"
            name="Registry only"
            stroke="var(--series-1)"
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)", fill: "var(--series-1)" }}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface-1)" }}
            isAnimationActive={false}
          />
          <Line
            dataKey="withNowcast"
            name="With media nowcast"
            stroke="var(--series-2)"
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)", fill: "var(--series-2)" }}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface-1)" }}
            label={endLabel}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
