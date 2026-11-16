import type { Feed } from "../data/types";
import { CATEGORIES, DEFAULT_FILTERS, OTHER, type Filters, type RangePreset } from "../model/analysis";
import { Icon } from "./Icon";

const PRESETS: { value: RangePreset; label: string }[] = [{ value: "7", label: "7 days" }, { value: "30", label: "30 days" }, { value: "90", label: "90 days" }, { value: "all", label: "All time" }];
export function FilterRow({ filters, feeds, count, onChange }: { filters: Filters; feeds: Feed[]; count: number; onChange: (next: Filters) => void }) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const active = filters.range !== "all" || filters.category !== "all" || filters.feed !== "all" || Boolean(filters.query);
  return (
    <section className="filter-panel" aria-label="Evidence filters">
      <div className="filter-heading">
        <span>Explore the evidence</span>
        <span className="filter-note">Filters update the news contribution, charts, and articles.</span>
      </div>
      <div className="filters">
        <label className="search-field">
          <Icon name="search" size={17} />
          <input type="search" placeholder="Search energy news…" aria-label="Search articles" value={filters.query} onChange={(e) => set({ query: e.target.value })} />
        </label>
        <select aria-label="Category" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
          <option value="all">All topics</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>
            {c[0].toUpperCase() + c.slice(1)}
          </option>)}
          <option value={OTHER}>Other / unclassified</option>
        </select>
        <select aria-label="Source" value={filters.feed} onChange={(e) => set({ feed: e.target.value })}>
          <option value="all">All news sources</option>
          {[...feeds].sort((a, b) => a.name.localeCompare(b.name)).map((f) => <option key={f.id} value={f.id}>
            {f.name}
          </option>)}
        </select>
        <div className="segmented" role="group" aria-label="Date range">
          {PRESETS.map((p) => <button key={p.value} aria-pressed={filters.range === p.value} onClick={() => set({ range: p.value })}>
            {p.label}
          </button>)}
        </div>
      </div>
      <div className="filter-footer">
        <span role="status">{count.toLocaleString()} matching article{count === 1 ? "" : "s"}</span>
        {active ? <button className="text-button" onClick={() => onChange(DEFAULT_FILTERS)}><Icon name="close" size={13} /> Clear filters</button> : <span>Dates are relative to the dataset snapshot</span>}
      </div>
    </section>
  );
}
