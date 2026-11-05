// Mirrors the columns the Supabase Data API exposes to the anon role
// (packages/db/migrations/versions/f626cc0b0c40_public_read_access_via_rls.py).

export interface Article {
  id: number;
  url: string;
  title: string;
  description: string | null;
  published_at: string | null; // ISO 8601
  category: string | null; // one of rules.yaml `categories`, or null
  feed_id: string;
}

export interface Feed {
  id: string;
  name: string;
  url: string;
  category: string;
  tags: string[];
}

export interface Dataset {
  articles: Article[];
  feeds: Feed[];
  /** "live" when read from Supabase, "sample" when using the bundled snapshot. */
  mode: "live" | "sample";
  /** When the data was produced (sample) or fetched (live). */
  asOf: Date;
}
