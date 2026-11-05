// How the consensus moved as articles accumulated: one point per week.

import type { Article } from "../data/types";
import { blend, type BlendSource } from "./consensus";
import { computeNowcast } from "./nowcast";

export interface TimelinePoint {
  date: Date;
  label: string;
  registryOnly: number;
  withNowcast: number;
  claims: number;
  articlesSeen: number;
}

const WEEK = 7 * 86_400_000;
const STEP_DRAWS = 6000;

export function toBlendSource(nc: { mean: number; sigma: number; weight: number }): BlendSource {
  return { year: nc.mean, sigma: nc.sigma, weight: nc.weight, censored: false };
}

export function consensusTimeline(
  articles: Article[],
  base: BlendSource[],
  asOf: Date,
  weeks = 12,
): TimelinePoint[] {
  const registryOnly = blend(base, STEP_DRAWS).median;
  const dated = articles.filter((a) => a.published_at).map((a) => ({ a, t: new Date(a.published_at!).getTime() }));
  const points: TimelinePoint[] = [];
  for (let i = weeks; i >= 0; i--) {
    const date = new Date(asOf.getTime() - i * WEEK);
    const seen = dated.filter((d) => d.t <= date.getTime());
    const nc = computeNowcast(seen.map((d) => d.a), date);
    points.push({
      date,
      label: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      registryOnly,
      withNowcast: nc ? blend([...base, toBlendSource(nc)], STEP_DRAWS).median : registryOnly,
      claims: nc?.claims.length ?? 0,
      articlesSeen: seen.length,
    });
  }
  return points;
}
