// Everything the page shows, derived from one dataset + one filter state, so
// every chart, tile, and list agrees on the same slice.

import type { Article, Dataset, Feed } from "../data/types";
import { blend, type BlendSource, type Consensus } from "./consensus";
import { computeNowcast, type Nowcast } from "./nowcast";
import { baselineSources, cleanRegistry, type Forecast } from "./registry";
import { consensusTimeline, toBlendSource, type TimelinePoint } from "./timeline";

export type RangePreset = "7" | "30" | "90" | "all";

export interface Filters {
  range: RangePreset;
  category: string; // "all" or a category
  feed: string; // "all" or a feed id
  query: string;
}

export const DEFAULT_FILTERS: Filters = { range: "all", category: "all", feed: "all", query: "" };

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

function weekStart(d: Date): Date {
  const w = new Date(d);
  w.setHours(0, 0, 0, 0);
  w.setDate(w.getDate() - ((w.getDay() + 6) % 7)); // Monday
  return w;
}

export function applyFilters(dataset: Dataset, filters: Filters): Article[] {
  const since = filters.range === "all" ? null : dataset.asOf.getTime() - Number(filters.range) * DAY;
  const q = filters.query.trim().toLowerCase();
  return dataset.articles
    .filter((a) => {
      if (since !== null) {
        if (!a.published_at) return false;
        if (new Date(a.published_at).getTime() < since) return false;
      }
      if (filters.category !== "all" && (a.category ?? OTHER) !== filters.category) return false;
      if (filters.feed !== "all" && a.feed_id !== filters.feed) return false;
      if (q && !`${a.title} ${a.description ?? ""}`.toLowerCase().includes(q)) return false;
      return true;
    })
    .sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""));
}

export function analyze(dataset: Dataset, filters: Filters): Analysis {
  const articles = applyFilters(dataset, filters);
  const feedsById = new Map(dataset.feeds.map((f) => [f.id, f]));

  const registry = cleanRegistry();
  const base: BlendSource[] = baselineSources(registry).map((r) => ({
    year: r.peakYear,
    sigma: r.sigma,
    weight: r.weight,
    censored: r.censored,
  }));

  const nowcast = computeNowcast(articles, dataset.asOf);
  const claimIds = new Map(nowcast?.claims.map((c) => [c.article.id, c.year]) ?? []);
  const registryOnly = blend(base);
  const withNowcast = nowcast ? blend([...base, toBlendSource(nowcast)]) : registryOnly;
  const timeline = consensusTimeline(articles, base, dataset.asOf);

  const weeks = new Map<number, WeekVolume>();
  for (const a of articles) {
    if (!a.published_at) continue;
    const ws = weekStart(new Date(a.published_at));
    const key = ws.getTime();
    let bucket = weeks.get(key);
    if (!bucket) {
      bucket = {
        weekStart: ws,
        label: ws.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        counts: {},
        total: 0,
      };
      weeks.set(key, bucket);
    }
    const cat = a.category ?? OTHER;
    bucket.counts[cat] = (bucket.counts[cat] ?? 0) + 1;
    bucket.total += 1;
  }
  const volume = [...weeks.values()].sort((a, b) => a.weekStart.getTime() - b.weekStart.getTime());
  const present = new Set(articles.map((a) => a.category ?? OTHER));
  const categoriesInView = [...CATEGORIES.filter((c) => present.has(c)), ...(present.has(OTHER) ? [OTHER] : [])];

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
