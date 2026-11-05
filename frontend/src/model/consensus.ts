// Credibility-weighted Monte-Carlo blend of peak-year positions.

export interface BlendSource {
  year: number;
  sigma: number;
  weight: number;
  censored: boolean;
}

export interface Consensus {
  median: number;
  p10: number;
  p90: number;
  pBy2030: number;
  pAlreadyPeaked: number;
  /** Probability mass per integer year, 2020..2060. */
  histogram: { year: number; p: number }[];
  draws: number;
}

export const CURRENT_YEAR = 2026;
const CENSOR_YEAR = 2050;
const CENSOR_SPREAD = 4;

/** Deterministic PRNG (mulberry32) so every render blends the same way. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function blend(sources: BlendSource[], draws = 20000, seed = 42): Consensus {
  const rand = rng(seed);
  const normal = () => {
    const u = Math.max(rand(), 1e-9);
    const v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  const total = sources.reduce((s, r) => s + r.weight, 0);
  const cumulative: number[] = [];
  let acc = 0;
  for (const r of sources) {
    acc += r.weight / total;
    cumulative.push(acc);
  }

  const out = new Float64Array(draws);
  for (let i = 0; i < draws; i++) {
    const u = rand();
    let j = cumulative.findIndex((c) => u <= c);
    if (j < 0) j = sources.length - 1;
    const r = sources[j];
    out[i] = r.censored ? CENSOR_YEAR + Math.abs(normal() * CENSOR_SPREAD) : r.year + normal() * r.sigma;
  }
  out.sort();

  const q = (p: number) => out[Math.min(draws - 1, Math.floor(p * draws))];
  const countLe = (y: number) => {
    let n = 0;
    for (let i = 0; i < draws && out[i] <= y; i++) n++;
    return n;
  };
  const bins = new Map<number, number>();
  for (let i = 0; i < draws; i++) {
    const y = Math.floor(out[i]);
    bins.set(y, (bins.get(y) ?? 0) + 1);
  }
  const histogram = [];
  for (let y = 2020; y <= 2060; y++) histogram.push({ year: y, p: (bins.get(y) ?? 0) / draws });

  return {
    median: q(0.5),
    p10: q(0.1),
    p90: q(0.9),
    pBy2030: countLe(2030) / draws,
    pAlreadyPeaked: countLe(CURRENT_YEAR - 1) / draws,
    histogram,
    draws,
  };
}
