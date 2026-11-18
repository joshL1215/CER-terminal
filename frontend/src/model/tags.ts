// Region and energy-type tags for articles, from plain keyword rules (no AI).
//
// The ingest job's `category` says what an article is about (grid, storage, policy…).
// These tags say WHERE it is about and WHICH energy it is about, so the news can be
// read against the client's question: are Asian countries moving away from oil
// toward EVs and solar?
//
// The rules are intentionally simple and visible. To change what counts as a
// region or an energy type, edit the patterns below. Matching runs on the title
// and summary, so an article can carry several tags or none.

import type { Article } from "../data/types";

export interface TagDef {
  id: string;
  label: string;
  /** Matches if ANY pattern matches the article's title + summary. */
  patterns: RegExp[];
}

// Case-insensitive unless a pattern needs the capitals (US, UK, UAE…).
export const REGIONS: TagDef[] = [
  {
    id: "china",
    label: "China",
    patterns: [/\b(?:china|chinese|beijing|shanghai|shenzhen|guangdong)\b/i],
  },
  {
    id: "india",
    label: "India",
    patterns: [/\b(?:india|indian(?! ocean)|new delhi|mumbai|bengaluru|gujarat|rajasthan)\b/i],
  },
  {
    id: "southeast-asia",
    label: "Southeast Asia",
    patterns: [/\b(?:southeast asia|south-east asia|asean|vietnam|indonesia|philippines|thailand|malaysia|singapore|myanmar|cambodia)\b/i],
  },
  {
    id: "japan-korea",
    label: "Japan & Korea",
    patterns: [/\b(?:japan|japanese|tokyo|korea|korean|seoul)\b/i],
  },
  {
    id: "middle-east",
    label: "Middle East",
    patterns: [
      /\b(?:middle east|saudi|emirates|iran|iranian|iraq|qatar|kuwait|bahrain|oman|israel|gaza|yemen|houthi|lebanon|syria)\b/i,
      /\b(?:strait of hormuz|hormuz|persian gulf|gulf states|gulf region)\b/i,
      /\bUAE\b/,
    ],
  },
  {
    id: "europe",
    label: "Europe",
    patterns: [
      /\b(?:europe|european|germany|german|france|french|britain|british|italy|italian|spain|spanish|poland|netherlands|nordic|norway|denmark|sweden)\b/i,
      /\b(?:EU|UK)\b/,
    ],
  },
  {
    id: "north-america",
    label: "North America",
    patterns: [
      /\b(?:united states|california|texas|canada|canadian|ontario|alberta|congress|ferc|mexico)\b/i,
      /\b(?:U\.S\.A?|USA|US)\b/,
    ],
  },
  {
    id: "oceania",
    label: "Australia & NZ",
    patterns: [/\b(?:australia|australian|queensland|new south wales|new zealand)\b/i],
  },
  {
    id: "africa",
    label: "Africa",
    patterns: [/\b(?:africa|african|nigeria|kenya|egypt|ethiopia|morocco|ghana)\b/i],
  },
  {
    id: "latin-america",
    label: "Latin America",
    patterns: [/\b(?:latin america|brazil|brazilian|chile|chilean|argentina|colombia|peru)\b/i],
  },
];

/** "Asia" is a group: any Asian country above, plus a few more and generic mentions. */
export const ASIA_MEMBERS = ["china", "india", "southeast-asia", "japan-korea"] as const;
const ASIA_EXTRA = /\b(?:asia|asian|asia-pacific|pakistan|bangladesh|sri lanka|nepal|taiwan|hong kong|mongolia)\b/i;
export const ASIA: TagDef = { id: "asia", label: "Asia (all)", patterns: [ASIA_EXTRA] };

/** What the article is about, fossil fuels first, then the technologies replacing them. */
export const ENERGY: TagDef[] = [
  {
    id: "oil",
    label: "Oil",
    patterns: [
      /\b(?:oil|crude|petroleum|gasoline|diesel|opec|refiner(?:y|ies)|barrels?)\b/i,
      // "gas cars" means gasoline cars, not natural gas.
      /\bgas(?:-powered| cars?| vehicles?| guzzlers?| engines?)\b|\bgas-guzzl/i,
    ],
  },
  {
    id: "gas",
    label: "Natural gas",
    patterns: [/\b(?:natural gas|fossil gas|lng|gas-fired|gas power|gas plants?|gas turbines?|gas prices?|gas demand|gas supply|methane)\b/i],
  },
  { id: "coal", label: "Coal", patterns: [/\bcoal\b/i] },
  { id: "solar", label: "Solar", patterns: [/\b(?:solar|photovoltaics?|pv)\b/i] },
  {
    id: "wind",
    label: "Wind",
    patterns: [/\b(?:offshore wind|onshore wind|wind (?:power|farms?|turbines?|energy|projects?|capacity|generation|auction))\b/i],
  },
  {
    id: "ev",
    label: "Electric vehicles",
    patterns: [
      /\b(?:evs?|bevs?|electric (?:vehicles?|cars?|buses|bus|trucks?|scooters?|two-wheelers?|motorcycles?)|plug-in hybrids?|e-buses|e-bus|charging stations?|ev charging)\b/i,
    ],
  },
  {
    id: "batteries",
    label: "Batteries & storage",
    patterns: [/\b(?:batter(?:y|ies)|energy storage|bess|lithium|sodium-ion|grid storage)\b/i],
  },
  { id: "nuclear", label: "Nuclear", patterns: [/\b(?:nuclear|reactors?|smrs?)\b/i] },
];

export const FOSSIL_ENERGY_IDS = ["oil", "gas", "coal"] as const;

export interface ArticleTags {
  regions: string[]; // ids, includes "asia" when any Asian region/term matched
  energy: string[]; // ids
}

function matches(def: TagDef, text: string): boolean {
  return def.patterns.some((p) => p.test(text));
}

export function tagText(text: string): ArticleTags {
  const regions = REGIONS.filter((r) => matches(r, text)).map((r) => r.id);
  if (matches(ASIA, text) || regions.some((r) => (ASIA_MEMBERS as readonly string[]).includes(r))) {
    regions.unshift(ASIA.id);
  }
  return { regions, energy: ENERGY.filter((e) => matches(e, text)).map((e) => e.id) };
}

const cache = new WeakMap<Article, ArticleTags>();

/** Tags for one article. Cached per article object, so filtering stays fast. */
export function tagArticle(a: Article): ArticleTags {
  let tags = cache.get(a);
  if (!tags) {
    tags = tagText(`${a.title} ${a.description ?? ""}`);
    cache.set(a, tags);
  }
  return tags;
}

/** Region options in display order: Asia group first, then each region. */
export const REGION_OPTIONS: TagDef[] = [ASIA, ...REGIONS];

const LABELS = new Map<string, string>([...REGION_OPTIONS, ...ENERGY].map((t) => [t.id, t.label]));
export function tagLabel(id: string): string {
  return LABELS.get(id) ?? id;
}

/** How many of the given articles carry each tag (for the filter dropdowns). */
export function tagCounts(articles: Article[]): { regions: Map<string, number>; energy: Map<string, number> } {
  const regions = new Map<string, number>();
  const energy = new Map<string, number>();
  for (const a of articles) {
    const t = tagArticle(a);
    for (const r of t.regions) regions.set(r, (regions.get(r) ?? 0) + 1);
    for (const e of t.energy) energy.set(e, (energy.get(e) ?? 0) + 1);
  }
  return { regions, energy };
}
