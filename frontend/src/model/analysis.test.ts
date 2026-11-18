import { describe, expect, it } from "vitest";
import type { Article, Dataset } from "../data/types";
import { analyze, applyFilters, articleCategories, DEFAULT_FILTERS } from "./analysis";

const base: Article = { id: 1, url: "https://news.example/1", title: "New battery research", description: null, published_at: "2026-11-16T12:00:00Z", category: "storage", feed_id: "lab" };
const dataset: Dataset = {
  mode: "live", asOf: new Date("2026-11-17T12:00:00Z"), totalArticles: 5,
  feeds: [{ id: "lab", name: "Energy Laboratory", url: "https://news.example/rss", category: "research", tags: ["science"] }],
  articles: [base,
    { ...base, id: 2, title: "Fossil fuels peak in 2030", category: "hydrogen", published_at: "2026-11-15T12:00:00Z" },
    { ...base, id: 3, category: null, published_at: null },
    { ...base, id: 4, published_at: "2025-01-01T12:00:00Z" },
    { ...base, id: 5, title: "Fossil fuels peak in 2031", published_at: "invalid" },
  ],
};

describe("features derived from pipeline articles", () => {
  it("searches titles, source names, feed tags, and real categories", () => {
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, query: "fossil" }).map((a) => a.id)).toEqual([2, 5]);
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, query: "Energy Laboratory" })).toHaveLength(5);
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, query: "science" })).toHaveLength(5);
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, query: "hydrogen" }).map((a) => a.id)).toEqual([2]);
  });

  it("combines source, category and date filters with valid date ordering", () => {
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, range: "7", feed: "lab", category: "storage" }).map((a) => a.id)).toEqual([1]);
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, category: "other" }).map((a) => a.id)).toEqual([3]);
    expect(applyFilters(dataset, { ...DEFAULT_FILTERS, feed: "missing" })).toEqual([]);
  });

  it("includes categories introduced by pipeline rules in controls and charts", () => {
    expect(articleCategories(dataset.articles)).toEqual(["storage", "hydrogen", "other"]);
    const result = analyze(dataset, DEFAULT_FILTERS);
    expect(result.categoriesInView).toContain("hydrogen");
    expect(result.volume.reduce((n, week) => n + week.total, 0)).toBe(3);
    expect(result.claimIds).toEqual(new Map([[2, 2030]]));
    expect(Number.isFinite(result.withNowcast.median)).toBe(true);
  });

  it("clears the news contribution when filters exclude the detected claims", () => {
    const result = analyze(dataset, { ...DEFAULT_FILTERS, category: "storage" });
    expect(result.claimIds.size).toBe(0);
    expect(result.nowcast).toBeNull();
    expect(result.withNowcast).toEqual(result.registryOnly);
  });
});
