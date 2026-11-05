import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CATEGORIES, OTHER, type WeekVolume } from "../model/analysis";
import { ChartCard } from "./ChartCard";
import { ChartTooltip } from "./ChartTooltip";

/** Category -> fixed categorical slot. Color follows the entity, never its rank. */
export function categoryColor(category: string): string {
  const i = (CATEGORIES as readonly string[]).indexOf(category);
  return i >= 0 ? `var(--series-${i + 1})` : "var(--series-other)";
}

export function VolumeChart({ volume, categories, dim }: { volume: WeekVolume[]; categories: string[]; dim?: boolean }) {
  const data = volume.map((w) => ({ label: w.label, ...w.counts, total: w.total }));
  const columns = [
    { key: "label", label: "Week of" },
    ...categories.map((c) => ({ key: c, label: c, numeric: true })),
    { key: "total", label: "Total", numeric: true },
  ];
  return (
    <ChartCard
      title="What the feed is talking about"
      subtitle="Kept articles per week by category"
      dim={dim}
      columns={columns}
      rows={data.map((d) => {
        const row: Record<string, string | number> = { label: d.label, total: d.total };
        for (const c of categories) row[c] = (d as Record<string, number | string>)[c] ?? 0;
        return row;
      })}
    >
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" strokeWidth={1} vertical={false} />
          <XAxis dataKey="label" stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
          <YAxis
            stroke="var(--axis)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            width={32}
            allowDecimals={false}
          />
          <Tooltip cursor={{ fill: "var(--hover-wash)" }} content={<ChartTooltip title={(l) => `Week of ${l}`} />} />
          <Legend iconType="rect" iconSize={10} wrapperStyle={{ fontSize: 12 }} />
          {categories.map((c, i) => (
            <Bar
              key={c}
              dataKey={c}
              name={c === OTHER ? "other / unclassified" : c}
              stackId="week"
              fill={categoryColor(c)}
              stroke="var(--surface-1)"
              strokeWidth={1}
              maxBarSize={24}
              radius={i === categories.length - 1 ? [4, 4, 0, 0] : 0}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
