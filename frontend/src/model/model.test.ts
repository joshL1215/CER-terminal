import { describe, expect, it } from "vitest";
import type { Article, Dataset } from "../data/types";
import { analyze, DEFAULT_FILTERS, weeklyVolume } from "./analysis";
import { blend } from "./consensus";

const article = (id: number, published_at: string, title = "Battery news"): Article =>
  ({ id, url: `https://news.example/${id}`, title, description: null, published_at, category: "storage", feed_id: "lab" });

describe("blend", () => {
  const sources = [{ year: 2026, sigma: 2, weight: 1, censored: false }];

  it("measures 'already peaked' against the as-of year", () => {
    expect(blend(sources, 2027).pAlreadyPeaked).toBeGreaterThan(blend(sources, 2026).pAlreadyPeaked);
  });

  it("keeps every draw in the histogram", () => {
    const wide = blend([...sources, { year: 2050, sigma: 3, weight: 1, censored: true }, { year: 2016, sigma: 3, weight: 1, censored: false }], 2026);
    expect(wide.histogram.reduce((n, b) => n + b.p, 0)).toBeCloseTo(1, 10);
  });
});

describe("weekly volume", () => {
  it("keeps empty weeks so the time axis is even", () => {
    const weeks = weeklyVolume([article(1, "2026-11-02T12:00:00Z"), article(2, "2026-11-23T12:00:00Z")]);
    expect(weeks.map((w) => w.total)).toEqual([1, 0, 0, 1]);
  });

  it("adds the year to labels when weeks span years", () => {
    const weeks = weeklyVolume([article(1, "2025-12-29T12:00:00Z"), article(2, "2026-01-05T12:00:00Z")]);
    expect(weeks[0].label).toMatch(/2025/);
  });
});

describe("timeline", () => {
  const dataset: Dataset = { mode: "live", asOf: new Date("2026-11-17T12:00:00Z"), totalArticles: 1, feeds: [], articles: [article(1, "2026-11-16T12:00:00Z")] };

  it("only goes back as far as the date filter", () => {
    expect(analyze(dataset, DEFAULT_FILTERS).timeline).toHaveLength(13);
    expect(analyze(dataset, { ...DEFAULT_FILTERS, range: "7" }).timeline).toHaveLength(2);
    expect(analyze(dataset, { ...DEFAULT_FILTERS, range: "30" }).timeline).toHaveLength(5);
  });
});
