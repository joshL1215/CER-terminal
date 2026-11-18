// Everything the page shows, derived from one dataset + one filter state, so
// every chart, tile, and list agrees on the same slice.

import type { Article, Dataset, Feed } from "../data/types";
import { blend, type BlendSource, type Consensus } from "./consensus";
import { computeNowcast, type Nowcast } from "./nowcast";
import { baselineSources, cleanRegistry, type Forecast } from "./registry";
import { tagArticle } from "./tags";
import { consensusTimeline, toBlendSource, type TimelinePoint } from "./timeline";

export type RangePreset = "7" | "30" | "90" | "all";

export interface Filters {
  range: RangePreset;
  category: string; // "all" or a category
  feed: string; // "all" or a feed id
  region: string; // "all" or a region tag id (see tags.ts)
  energy: string; // "all" or an energy tag id (see tags.ts)
  query: string;
}

export const DEFAULT_FILTERS: Filters = { range: "all", category: "all", feed: "all", region: "all", energy: "all", query: "" };

/** Fixed order = fixed color slot; a category keeps its hue whatever is filtered. */
export const CATEGORIES = [
  "grid",
  "generation",
  "storage",
  "markets",
  "policy",
  "transportation",
  "buildings",
  "research",
] as const;
export const OTHER = "other";

/** Keep familiar topics in a stable order and include new pipeline categories. */
export function articleCategories(articles: Article[]): string[] {
  const present = new Set(articles.map((a) => a.category ?? OTHER));
  const known: string[] = CATEGORIES.filter((c) => present.delete(c));
  const hasOther = present.delete(OTHER);
  return [...known, ...[...present].sort(), ...(hasOther ? [OTHER] : [])];
}

export interface WeekVolume {
  label: string;
  weekStart: Date;
  counts: Record<string, number>;
  total: number;
}

export interface Analysis {
  articles: Article[]; // filtered, newest first
  feedsById: Map<string, Feed>;
  registry: Forecast[];
  nowcast: Nowcast | null;
  claimIds: Map<number, number>; // article id -> claimed peak year
  registryOnly: Consensus;
  withNowcast: Consensus;
  timeline: TimelinePoint[];
  volume: WeekVolume[];
  categoriesInView: string[];
}

const DAY = 86_400_000;

const TIMELINE_WEEKS = 12;

// The registry is fixed, so its blend only depends on the as-of year. Caching it
// keeps typing in the search box from re-running 20,000 draws on every keystroke.
const registryCache = new Map<number, { registry: Forecast[]; base: BlendSource[]; registryOnly: Consensus }>();
function registryBlend(year: number) {
  let cached = registryCache.get(year);
  if (!cached) {
    const registry = cleanRegistry();
    const base: BlendSource[] = baselineSources(registry).map((r) => ({
      year: r.peakYear,
      sigma: r.sigma,
      weight: r.weight,
      censored: r.censored,
    }));
    cached = { registry, base, registryOnly: blend(base, year) };
    registryCache.set(year, cached);
  }
  return cached;
}

function weekStart(d: Date): Date {
  const w = new Date(d);
  w.setHours(0, 0, 0, 0);
  w.setDate(w.getDate() - ((w.getDay() + 6) % 7)); // Monday
  return w;
}

/** Articles per week by category, with empty weeks kept so the time axis is even. */
export function weeklyVolume(articles: Article[]): WeekVolume[] {
  const counts = new Map<number, Record<string, number>>();
  for (const a of articles) {
    if (!a.published_at) continue;
    const t = Date.parse(a.published_at);
    if (!Number.isFinite(t)) continue;
    const key = weekStart(new Date(t)).getTime();
    const bucket = counts.get(key) ?? {};
    const cat = a.category ?? OTHER;
    bucket[cat] = (bucket[cat] ?? 0) + 1;
    counts.set(key, bucket);
  }
  if (!counts.size) return [];
  const keys = [...counts.keys()];
  const first = new Date(Math.min(...keys));
  const last = Math.max(...keys);
  const spansYears = first.getFullYear() !== new Date(last).getFullYear();
  const volume: WeekVolume[] = [];
  for (const w = new Date(first); w.getTime() <= last; w.setDate(w.getDate() + 7)) {
    const weekCounts = counts.get(w.getTime()) ?? {};
    volume.push({
      weekStart: new Date(w),
      label: w.toLocaleDateString(undefined, spansYears ? { year: "numeric", month: "short", day: "numeric" } : { month: "short", day: "numeric" }),
      counts: weekCounts,
      total: Object.values(weekCounts).reduce((n, c) => n + c, 0),
    });
  }
  return volume;
}

export function applyFilters(dataset: Dataset, filters: Filters): Article[] {
  const since = filters.range === "all" ? null : dataset.asOf.getTime() - Number(filters.range) * DAY;
  const q = filters.query.trim().toLowerCase();
  const feedsById = new Map(dataset.feeds.map((f) => [f.id, f]));
  return dataset.articles
    .filter((a) => {
      if (since !== null) {
        if (!a.published_at) return false;
        const timestamp = new Date(a.published_at).getTime();
        if (!Number.isFinite(timestamp) || timestamp < since || timestamp > dataset.asOf.getTime()) return false;
      }
      if (filters.category !== "all" && (a.category ?? OTHER) !== filters.category) return false;
      if (filters.feed !== "all" && a.feed_id !== filters.feed) return false;
      if (filters.region !== "all" || filters.energy !== "all") {
        const tags = tagArticle(a);
        if (filters.region !== "all" && !tags.regions.includes(filters.region)) return false;
        if (filters.energy !== "all" && !tags.energy.includes(filters.energy)) return false;
      }
      const feed = feedsById.get(a.feed_id);
      if (q && !`${a.title} ${a.description ?? ""} ${feed?.name ?? ""} ${a.category ?? OTHER} ${feed?.tags.join(" ") ?? ""}`.toLowerCase().includes(q)) return false;
      return true;
    })
    .sort((a, b) => (b.published_at ? Date.parse(b.published_at) || 0 : 0) - (a.published_at ? Date.parse(a.published_at) || 0 : 0) || b.id - a.id);
}

export function analyze(dataset: Dataset, filters: Filters): Analysis {
  const articles = applyFilters(dataset, filters);
  const feedsById = new Map(dataset.feeds.map((f) => [f.id, f]));

  const year = dataset.asOf.getFullYear();
  const { registry, base, registryOnly } = registryBlend(year);

  const nowcast = computeNowcast(articles, dataset.asOf);
  const claimIds = new Map(nowcast?.claims.map((c) => [c.article.id, c.year]) ?? []);
  const withNowcast = nowcast ? blend([...base, toBlendSource(nowcast)], year) : registryOnly;
  // Only go back as far as the date filter allows, so earlier points don't look news-free.
  const timelineWeeks = filters.range === "all" ? TIMELINE_WEEKS : Math.max(1, Math.min(TIMELINE_WEEKS, Math.floor(Number(filters.range) / 7)));
  const timeline = consensusTimeline(articles, base, dataset.asOf, registryOnly.median, timelineWeeks);

  const volume = weeklyVolume(articles);
  const categoriesInView = articleCategories(articles);

  return {
    articles,
    feedsById,
    registry,
    nowcast,
    claimIds,
    registryOnly,
    withNowcast,
    timeline,
    volume,
    categoriesInView,
  };
}
