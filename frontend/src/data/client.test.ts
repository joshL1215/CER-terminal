// Exercise the real Supabase query builder against HTTP responses, including
// column grants and server-side pagination, rather than mocking its chain API.
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Article, Feed } from "./types";

const feed: Feed = { id: "energy", name: "Energy source", url: "https://energy.example/feed", category: "research", tags: [] };
const article: Article = { id: 1, url: "https://energy.example/article", title: "Fossil fuels peak in 2030", description: "A new report", published_at: "2026-11-16T12:00:00Z", category: "research", feed_id: feed.id };

function mockApi(articles: Article[], feeds: Feed[] = [feed], pageLimit = 1000) {
  const requests: URL[] = [];
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    requests.push(url);
    const headers = new Headers(init?.headers);
    expect(headers.get("apikey")).toBe("test-public-key");
    const all = url.pathname.endsWith("/articles") ? articles : feeds;
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const limit = Math.min(pageLimit, Number(url.searchParams.get("limit") ?? 1000));
    const rows = all.slice(offset, offset + limit);
    return new Response(JSON.stringify(rows), {
      status: 200,
      headers: { "Content-Type": "application/json", "Content-Range": `${offset}-${offset + rows.length - 1}/${all.length}` },
    });
  });
  vi.stubGlobal("fetch", fetch);
  return requests;
}

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_SUPABASE_URL", "https://project.supabase.co");
  vi.stubEnv("VITE_SUPABASE_ANON_KEY", "test-public-key");
});

describe("pipeline article loading", () => {
  it("reads public columns and every page even below Supabase's default row limit", async () => {
    const articles = Array.from({ length: 5 }, (_, i) => ({ ...article, id: i + 1 }));
    const feeds = [feed, { ...feed, id: "second" }, { ...feed, id: "third" }];
    const requests = mockApi(articles, feeds, 2);
    const { loadDataset, initialDataset } = await import("./client");
    expect(initialDataset().articles).toEqual([]);
    const result = await loadDataset();
    expect(result).toMatchObject({ articles, feeds, mode: "live", totalArticles: 5 });
    const articleRequests = requests.filter((r) => r.pathname.endsWith("/articles"));
    expect(articleRequests.map((r) => Number(r.searchParams.get("offset")))).toEqual([0, 2, 4]);
    expect(articleRequests[0].searchParams.get("select")).toBe("id,url,title,description,published_at,category,feed_id");
    expect(articleRequests[0].searchParams.get("order")).toBe("published_at.desc.nullslast,id.desc");
    const feedRequests = requests.filter((r) => r.pathname.endsWith("/feeds"));
    expect(feedRequests).toHaveLength(2);
    expect(feedRequests[0].searchParams.get("select")).toBe("id,name,url,category,tags");
    // status and active are private columns: visibility is enforced by RLS.
    expect(requests.every((r) => !r.searchParams.has("status") && !r.searchParams.has("active"))).toBe(true);
  });

  it("returns an empty live dataset when no screened articles exist", async () => {
    mockApi([]);
    const { loadDataset } = await import("./client");
    expect(await loadDataset()).toMatchObject({ mode: "live", articles: [], totalArticles: 0 });
  });

  it("reports the full row count when the 5000-article browser limit is reached", async () => {
    mockApi(Array.from({ length: 5002 }, (_, i) => ({ ...article, id: i + 1 })), [feed], 600);
    const { loadDataset } = await import("./client");
    const result = await loadDataset();
    expect(result.articles).toHaveLength(5000);
    expect(result.totalArticles).toBe(5002);
  });

  it("surfaces API failures without substituting sample articles", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ message: "permission denied", code: "42501" }), { status: 403 })));
    const { loadDataset } = await import("./client");
    await expect(loadDataset()).rejects.toThrow(/permission denied/);
  });

  it("does not make HTTP requests with only one setting configured", async () => {
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const { loadDataset, isLiveConfigured } = await import("./client");
    expect(isLiveConfigured).toBe(true);
    await expect(loadDataset()).rejects.toThrow(/VITE_SUPABASE_ANON_KEY/);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("keeps sample mode available when no live connection is configured", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");
    const { loadDataset } = await import("./client");
    const result = await loadDataset();
    expect(result.mode).toBe("sample");
    expect(result.articles.length).toBeGreaterThan(0);
  });
});
