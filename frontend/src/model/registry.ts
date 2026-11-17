// Published positions on when global fossil fuel consumption peaks.
// This is the hand-curated "major sources" layer; articles never edit it
// directly (see nowcast.ts for how news enters the blend).

export type Scenario = "baseline" | "policy" | "netzero";
export type SourceType = "institutional" | "industry" | "ngo" | "academic";

export interface Forecast {
  org: string;
  report: string;
  published: number; // report year; the newest edition per org/scenario wins
  scenario: Scenario;
  sourceType: SourceType;
  peakYear: number;
  /** true = the source sees no peak before 2050 (right-censored at 2050). */
  censored: boolean;
  /** Credibility prior: methodology transparency + track record − conflict of interest. */
  weight: number;
  /** ± years implied by the source's own framing. */
  sigma: number;
  verified: boolean;
  note?: string;
}

const f = (
  org: string,
  report: string,
  published: number,
  scenario: Scenario,
  sourceType: SourceType,
  peakYear: number,
  censored: boolean,
  weight: number,
  sigma: number,
  verified = true,
  note?: string,
): Forecast => ({ org, report, published, scenario, sourceType, peakYear, censored, weight, sigma, verified, note });

export const REGISTRY: Forecast[] = [
  f("DNV", "Energy Transition Outlook 2024", 2024, "baseline", "institutional", 2025, false, 1.0, 1.5, true,
    "Replace with the ETO 2026 primary-data peak once extracted from the team's workbook."),
  f("IEA", "WEO 2024 — STEPS", 2024, "baseline", "institutional", 2029, false, 1.0, 2.0, true,
    "All three fossil fuels peak before 2030."),
  f("IEA", "WEO 2024 — APS", 2024, "policy", "institutional", 2025, false, 1.0, 1.5),
  f("IEA", "WEO 2024 — NZE", 2024, "netzero", "institutional", 2024, false, 1.0, 1.0),
  f("BP", "Energy Outlook 2024 — Current Trajectory", 2024, "baseline", "industry", 2027, false, 0.8, 2.5),
  f("Shell", "Energy Security Scenarios", 2023, "baseline", "industry", 2028, false, 0.7, 3.0),
  f("Equinor", "Energy Perspectives 2024", 2024, "baseline", "industry", 2030, false, 0.7, 3.0),
  f("McKinsey", "Global Energy Perspective 2024", 2024, "baseline", "institutional", 2028, false, 0.8, 2.5),
  f("Rystad Energy", "Energy Transition Report 2024", 2024, "baseline", "industry", 2026, false, 0.7, 2.0),
  f("Wood Mackenzie", "Energy Transition Outlook 2024", 2024, "baseline", "industry", 2032, false, 0.7, 3.0),
  f("BloombergNEF", "New Energy Outlook 2024 — ETS", 2024, "baseline", "institutional", 2025, false, 0.9, 1.5),
  f("Ember", "Global Electricity Review 2025", 2025, "baseline", "ngo", 2024, false, 0.8, 1.5,
    true, "Power-sector fossil generation plateau."),
  f("RMI", "Peaking: the series (2023)", 2023, "baseline", "ngo", 2025, false, 0.7, 1.5),
  f("Carbon Tracker", "Peak fossil demand (2023)", 2023, "baseline", "ngo", 2025, false, 0.6, 2.0),
  f("OPEC", "World Oil Outlook 2024", 2024, "baseline", "industry", 2050, true, 0.5, 3.0, true, "No peak before 2050."),
  f("ExxonMobil", "Global Outlook 2024", 2024, "baseline", "industry", 2050, true, 0.5, 3.0, true, "Plateau, no decline before 2050."),
  f("US EIA", "IEO 2023 — Reference", 2023, "baseline", "institutional", 2050, true, 0.8, 3.0, true,
    "Reference case: global fossil use still rising in 2050."),
  f("IRENA", "WETO 2024 — 1.5°C", 2024, "netzero", "institutional", 2024, false, 0.8, 1.5),
  f("IEEFA", "Stance proxy — unverified", 2024, "baseline", "ngo", 2026, false, 0.5, 2.0, false,
    "IEEFA publishes no single peak-year forecast; 2026 encodes their editorial stance."),
  f("Academic pool", "Stance proxy — unverified", 2024, "baseline", "academic", 2026, false, 0.9, 2.5, false,
    "Placeholder for pooled peer-reviewed estimates."),
  // Older editions, kept to show vintage dedupe in action (the cleaner drops them).
  f("IEA", "WEO 2022 — STEPS", 2022, "baseline", "institutional", 2032, false, 1.0, 2.0),
  f("BP", "Energy Outlook 2022", 2022, "baseline", "industry", 2030, false, 0.8, 3.0),
];

/** One voice per (org, scenario): the newest report wins; implausible years dropped. */
export function cleanRegistry(raw: Forecast[] = REGISTRY): Forecast[] {
  const latest = new Map<string, Forecast>();
  for (const r of raw) {
    const key = `${r.org}|${r.scenario}`;
    const cur = latest.get(key);
    if (!cur || r.published > cur.published) latest.set(key, r);
  }
  return [...latest.values()].filter((r) => r.peakYear >= 2015 && r.peakYear <= 2060);
}

export function baselineSources(clean: Forecast[]): Forecast[] {
  return clean.filter((r) => r.scenario === "baseline");
}
