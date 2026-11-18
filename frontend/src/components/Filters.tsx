import type { Feed } from "../data/types";
import { DEFAULT_FILTERS, OTHER, type Filters, type RangePreset } from "../model/analysis";
import { ENERGY, REGION_OPTIONS, tagCounts } from "../model/tags";
import { Icon } from "./Icon";

const PRESETS: { value: RangePreset; label: string }[] = [{ value: "7", label: "7 days" }, { value: "30", label: "30 days" }, { value: "90", label: "90 days" }, { value: "all", label: "All time" }];
type TagCounts = ReturnType<typeof tagCounts>;
export function FilterRow({ filters, feeds, categories, count, tags, onChange }: { filters: Filters; feeds: Feed[]; categories: string[]; count: number; tags: TagCounts; onChange: (next: Filters) => void }) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const active = filters.range !== "all" || filters.category !== "all" || filters.feed !== "all" || filters.region !== "all" || filters.energy !== "all" || Boolean(filters.query);
  // Options with no articles in the dataset are disabled, so a choice never leads to an empty page by itself.
  const option = (def: { id: string; label: string }, counts: Map<string, number>, selected: string) => {
    const n = counts.get(def.id) ?? 0;
    return <option key={def.id} value={def.id} disabled={n === 0 && def.id !== selected}>{def.label} ({n})</option>;
  };
  return (
    <section className="filter-panel" aria-label="Evidence filters">
      <div className="filter-heading">
        <span>Filters</span>
        <span className="filter-note">These change the charts, the article list and the news part of the estimate.</span>
      </div>
      <div className="filters">
        <label className="search-field">
          <Icon name="search" size={17} />
          <input type="search" placeholder="Search energy news…" aria-label="Search articles" value={filters.query} onChange={(e) => set({ query: e.target.value })} />
        </label>
        <select aria-label="Category" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
          <option value="all">All topics</option>
          {categories.map((c) => <option key={c} value={c}>
            {c === OTHER ? "Other / unclassified" : c[0].toUpperCase() + c.slice(1)}
          </option>)}
        </select>
        <select aria-label="Source" value={filters.feed} onChange={(e) => set({ feed: e.target.value })}>
          <option value="all">All news sources</option>
          {[...feeds].sort((a, b) => a.name.localeCompare(b.name)).map((f) => <option key={f.id} value={f.id}>
            {f.name}
          </option>)}
        </select>
        <select aria-label="Region" value={filters.region} onChange={(e) => set({ region: e.target.value })}>
          <option value="all">All regions</option>
          {REGION_OPTIONS.map((r) => option(r, tags.regions, filters.region))}
        </select>
        <select aria-label="Energy type" value={filters.energy} onChange={(e) => set({ energy: e.target.value })}>
          <option value="all">All energy types</option>
          {ENERGY.map((e) => option(e, tags.energy, filters.energy))}
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
