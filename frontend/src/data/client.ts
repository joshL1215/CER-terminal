import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import sample from "./sample.json";
import type { Article, Dataset, Feed } from "./types";

// RLS grants are per column, so `select=*` is rejected: list the public columns.
const ARTICLE_COLUMNS = "id, url, title, description, published_at, category, feed_id";
const FEED_COLUMNS = "id, name, url, category, tags";
const PAGE = 1000;
const MAX_ARTICLES = 5000;

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isLiveConfigured = Boolean(url && anonKey);

let client: SupabaseClient | null = null;
function getClient(): SupabaseClient {
  if (!client) client = createClient(url!, anonKey!);
  return client;
}

async function fetchArticles(): Promise<Article[]> {
  const rows: Article[] = [];
  for (let from = 0; from < MAX_ARTICLES; from += PAGE) {
    const { data, error } = await getClient()
      .from("articles")
      .select(ARTICLE_COLUMNS)
      .order("published_at", { ascending: false, nullsFirst: false })
      .range(from, from + PAGE - 1);
    if (error) throw new Error(`articles: ${error.message}`);
    rows.push(...(data as Article[]));
    if (data.length < PAGE) break;
  }
  return rows;
}

async function fetchFeeds(): Promise<Feed[]> {
  const { data, error } = await getClient().from("feeds").select(FEED_COLUMNS);
  if (error) throw new Error(`feeds: ${error.message}`);
  return data as Feed[];
}

export function loadSample(): Dataset {
  return {
    articles: sample.articles as Article[],
    feeds: sample.feeds as Feed[],
    mode: "sample",
    asOf: new Date(sample.generated),
  };
}

export async function loadDataset(): Promise<Dataset> {
  if (!isLiveConfigured) return loadSample();
  const [articles, feeds] = await Promise.all([fetchArticles(), fetchFeeds()]);
  return { articles, feeds, mode: "live", asOf: new Date() };
}
