// Media nowcast: kept articles that make a directional claim about the fossil
// peak are blended as ONE capped, recency-decayed pseudo-source. News can move
// the number between report vintages but can never outweigh the registry.

import type { Article } from "../data/types";

export interface PeakClaim {
  article: Article;
  year: number;
  /** Recency weight in [0, 1] at the as-of date. */
  w: number;
  phrase: string;
}

export interface Nowcast {
  mean: number;
  sigma: number;
  weight: number;
  claims: PeakClaim[];
}

export const NOWCAST_MAX_WEIGHT = 0.5; // half an IEA
export const NOWCAST_HALF_LIFE_DAYS = 60;
const MIN_SIGMA = 2;
const DAY = 86_400_000;

const EXPLICIT_YEAR = /peak(?:ed|ing)?[^.]{0,40}?\bin\s+(20\d\d)/;
const ALREADY = /already peaked|past (?:the )?peak|peak (?:is|was) behind|peaked in|has peaked|have peaked/;
const NEARING = /near(?:s|ing)? (?:the )?peak|approach(?:es|ing) (?:the )?peak|plateau|peak (?:this|next) year/;
const NO_PEAK = /no peak|won'?t peak|will not peak|far from (?:a )?peak|keeps? (?:rising|growing)/;
const FOSSIL = /fossil|\boil\b|\bcoal\b|\bgas\b|\bcrude\b|emissions?|carbon/;

/** The claimed peak year an article implies, or null if it makes no claim. */
export function extractClaim(text: string, publishedYear: number): { year: number; phrase: string } | null {
  const blob = text.toLowerCase();
  if (!FOSSIL.test(blob)) return null;
  const explicit = blob.match(EXPLICIT_YEAR);
  if (explicit) return { year: Number(explicit[1]), phrase: explicit[0] };
  const already = blob.match(ALREADY);
  if (already) return { year: publishedYear - 1, phrase: already[0] };
  const nearing = blob.match(NEARING);
  if (nearing) return { year: publishedYear + 1, phrase: nearing[0] };
  const none = blob.match(NO_PEAK);
  if (none) return { year: 2045, phrase: none[0] };
  return null;
}

export function peakClaims(articles: Article[], asOf: Date): PeakClaim[] {
  const claims: PeakClaim[] = [];
  for (const article of articles) {
    if (!article.published_at) continue;
    const published = new Date(article.published_at);
    if (published > asOf) continue;
    const claim = extractClaim(`${article.title} ${article.description ?? ""}`, published.getFullYear());
    if (!claim || claim.year < 2015 || claim.year > 2060) continue;
    const ageDays = Math.max(0, (asOf.getTime() - published.getTime()) / DAY);
    claims.push({ article, year: claim.year, w: Math.pow(0.5, ageDays / NOWCAST_HALF_LIFE_DAYS), phrase: claim.phrase });
  }
  return claims;
}

export function computeNowcast(articles: Article[], asOf: Date): Nowcast | null {
  const claims = peakClaims(articles, asOf);
  if (!claims.length) return null;
  const W = claims.reduce((s, c) => s + c.w, 0);
  const mean = claims.reduce((s, c) => s + c.year * c.w, 0) / W;
  const variance = claims.reduce((s, c) => s + c.w * (c.year - mean) ** 2, 0) / W;
  return {
    mean,
    sigma: Math.max(MIN_SIGMA, Math.sqrt(variance)),
    weight: Math.min(NOWCAST_MAX_WEIGHT, 0.15 * Math.sqrt(W) * Math.sqrt(claims.length)),
    claims,
  };
}
