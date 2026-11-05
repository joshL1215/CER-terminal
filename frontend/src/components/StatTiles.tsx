import type { Analysis } from "../model/analysis";
import { NOWCAST_MAX_WEIGHT } from "../model/nowcast";

export function StatTiles({ analysis }: { analysis: Analysis }) {
  const { withNowcast, registryOnly, nowcast, articles, registry } = analysis;
  const shift = withNowcast.median - registryOnly.median;
  const baseline = registry.filter((r) => r.scenario === "baseline").length;
  return (
    <div className="tiles">
      <div className="tile hero">
        <div className="label">Consensus peak year</div>
        <div className="value">{withNowcast.median.toFixed(0)}</div>
        <div className="delta">
          p10–p90 {withNowcast.p10.toFixed(0)}–{withNowcast.p90.toFixed(0)}
          {nowcast ? ` · news shifts it ${shift >= 0 ? "+" : ""}${shift.toFixed(1)} yr` : " · registry only"}
        </div>
      </div>
      <div className="tile">
        <div className="label">Chance the peak is by 2030</div>
        <div className="value">{(withNowcast.pBy2030 * 100).toFixed(0)}%</div>
        <div className="delta">already peaked: {(withNowcast.pAlreadyPeaked * 100).toFixed(0)}%</div>
      </div>
      <div className="tile">
        <div className="label">Major sources blended</div>
        <div className="value">{baseline}</div>
        <div className="delta">baseline scenarios, newest edition per org</div>
      </div>
      <div className="tile">
        <div className="label">Articles in view</div>
        <div className="value">{articles.length}</div>
        <div className="delta">kept by the LLM screen</div>
      </div>
      <div className="tile">
        <div className="label">Peak claims in the news</div>
        <div className="value">{nowcast?.claims.length ?? 0}</div>
        <div className="delta">
          {nowcast
            ? `nowcast weight ${nowcast.weight.toFixed(2)} of max ${NOWCAST_MAX_WEIGHT}`
            : "no directional claims in view"}
        </div>
      </div>
    </div>
  );
}
