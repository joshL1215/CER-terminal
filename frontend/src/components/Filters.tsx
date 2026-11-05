import type { Feed } from "../data/types";
import { CATEGORIES, OTHER, type Filters, type RangePreset } from "../model/analysis";

const PRESETS: { value: RangePreset; label: string }[] = [
  { value: "7", label: "7d" },
  { value: "30", label: "30d" },
  { value: "90", label: "90d" },
  { value: "all", label: "All" },
];

interface Props {
  filters: Filters;
  feeds: Feed[];
  count: number;
  onChange: (next: Filters) => void;
}

export function FilterRow({ filters, feeds, count, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  return (
    <div className="filters" role="group" aria-label="Filters">
      <div className="segmented" role="group" aria-label="Date range">
        {PRESETS.map((p) => (
          <button key={p.value} aria-pressed={filters.range === p.value} onClick={() => set({ range: p.value })}>
            {p.label}
          </button>
        ))}
      </div>
      <select aria-label="Category" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
        <option value="all">All categories</option>
        {CATEGORIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
        <option value={OTHER}>other / unclassified</option>
      </select>
      <select aria-label="Source" value={filters.feed} onChange={(e) => set({ feed: e.target.value })}>
        <option value="all">All sources</option>
        {[...feeds]
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
      </select>
      <input
        type="search"
        placeholder="Search titles…"
        aria-label="Search"
        value={filters.query}
        onChange={(e) => set({ query: e.target.value })}
      />
      <span className="spacer" />
      <span className="count">
        {count} article{count === 1 ? "" : "s"} in view
      </span>
    </div>
  );
}
