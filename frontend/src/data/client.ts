import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import sample from "./sample.json";
import { isLiveConfigured, readDataConfig } from "./config";
import type { Article, Dataset, Feed } from "./types";

export { isLiveConfigured } from "./config";

// RLS grants are per column, so `select=*` is rejected: list the public columns.
const ARTICLE_COLUMNS = "id, url, title, description, published_at, category, feed_id";
const FEED_COLUMNS = "id, name, url, category, tags";
const PAGE = 1000;
const MAX_ARTICLES = 5000;

let client: SupabaseClient | null = null;
function getClient(): SupabaseClient {
  if (!client) {
    const config = readDataConfig(import.meta.env);
    if (!config) throw new Error("Live data is not configured.");
    client = createClient(config.url, config.publicKey, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    });
  }
  return client;
}

async function fetchArticles(signal: AbortSignal): Promise<{ articles: Article[]; totalArticles: number }> {
  const rows: Article[] = [];
  let totalArticles: number | null = null;
  while (rows.length < MAX_ARTICLES) {
    const from = rows.length;
    const { data, error, count } = await getClient()
      .from("articles")
      .select(ARTICLE_COLUMNS, from === 0 ? { count: "exact" } : {})
      .order("published_at", { ascending: false, nullsFirst: false })
      .order("id", { ascending: false })
      .range(from, Math.min(from + PAGE, MAX_ARTICLES) - 1)
      .abortSignal(signal);
    if (error) throw new Error(`articles: ${error.message}`);
    if (count !== null) totalArticles = count;
    rows.push(...(data as Article[]));
    // Advance by the rows actually returned: the project's API row limit can
    // be smaller than PAGE. An exact count avoids mistaking a short page for EOF.
    if (!data.length || (totalArticles !== null && rows.length >= totalArticles)) break;
  }
  return { articles: rows, totalArticles: totalArticles ?? rows.length };
}

async function fetchFeeds(signal: AbortSignal): Promise<Feed[]> {
  const rows: Feed[] = [];
  let total: number | null = null;
  while (true) {
    const { data, error, count } = await getClient().from("feeds")
      .select(FEED_COLUMNS, rows.length === 0 ? { count: "exact" } : {})
      .order("id")
      .range(rows.length, rows.length + PAGE - 1)
      .abortSignal(signal);
    if (error) throw new Error(`feeds: ${error.message}`);
    if (count !== null) total = count;
    rows.push(...(data as Feed[]));
    if (!data.length || (total !== null && rows.length >= total)) return rows;
  }
}

export function loadSample(): Dataset {
  return {
    articles: sample.articles as Article[],
    feeds: sample.feeds as Feed[],
    mode: "sample",
    asOf: new Date(sample.generated),
    totalArticles: sample.articles.length,
  };
}

/** No sample rows are presented as live while a request is loading or failing. */
export function initialDataset(): Dataset {
  return isLiveConfigured
    ? { articles: [], feeds: [], mode: "live", asOf: new Date(), totalArticles: 0 }
    : loadSample();
}

export async function loadDataset(signal?: AbortSignal): Promise<Dataset> {
  if (!isLiveConfigured) return loadSample();
  const timeout = AbortSignal.timeout(30_000);
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout;
  const [{ articles, totalArticles }, feeds] = await Promise.all([fetchArticles(requestSignal), fetchFeeds(requestSignal)]);
  return { articles, feeds, totalArticles, mode: "live", asOf: new Date() };
}
