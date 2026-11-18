export interface DataConfig {
  url: string;
  publicKey: string;
}

/** Missing settings enable the demo; incomplete settings are a connection error. */
export function readDataConfig(env: Record<string, unknown>): DataConfig | null {
  const value = (key: string) => typeof env[key] === "string" ? env[key].trim() : "";
  const url = value("VITE_SUPABASE_URL");
  const publicKey = value("VITE_SUPABASE_ANON_KEY");
  if (!url && !publicKey) return null;
  if (!url || !publicKey) {
    throw new Error("Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env.local, then restart Vite.");
  }
  let parsed: URL;
  try { parsed = new URL(url); } catch { throw new Error("VITE_SUPABASE_URL must be a valid http(s) project URL."); }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("VITE_SUPABASE_URL must be a valid http(s) project URL.");
  }
  return { url: parsed.href.replace(/\/$/, ""), publicKey };
}

export const isLiveConfigured = ["VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"]
  .some((key) => Boolean(import.meta.env[key]?.trim()));
