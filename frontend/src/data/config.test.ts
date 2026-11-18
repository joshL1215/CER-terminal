import { describe, expect, it } from "vitest";
import { readDataConfig } from "./config";

describe("frontend connection settings", () => {
  it("uses sample mode only when both settings are absent", () => {
    expect(readDataConfig({})).toBeNull();
    expect(readDataConfig({ VITE_SUPABASE_URL: "  ", VITE_SUPABASE_ANON_KEY: "" })).toBeNull();
  });

  it.each([
    { VITE_SUPABASE_URL: "https://project.supabase.co" },
    { VITE_SUPABASE_ANON_KEY: "public-key" },
    { VITE_SUPABASE_URL: "bad-url", VITE_SUPABASE_ANON_KEY: "public-key" },
    { VITE_SUPABASE_URL: "file:///tmp/db", VITE_SUPABASE_ANON_KEY: "public-key" },
  ])("reports incomplete or invalid settings instead of silently loading samples: %j", (env) => {
    expect(() => readDataConfig(env)).toThrow(/VITE_SUPABASE/);
  });

  it("trims settings and supports local Supabase URLs", () => {
    expect(readDataConfig({ VITE_SUPABASE_URL: " http://localhost:54321/ ", VITE_SUPABASE_ANON_KEY: " public-key " }))
      .toEqual({ url: "http://localhost:54321", publicKey: "public-key" });
  });
});
