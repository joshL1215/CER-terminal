import type { Analysis } from "../model/analysis";
import type { Consensus } from "../model/consensus";
import { Icon } from "./Icon";

export function StatTiles({ analysis, consensus, onNews, onSources }: { analysis: Analysis; consensus: Consensus; onNews: (signals?: boolean) => void; onSources: () => void }) {
  const { articles, registry, claimIds } = analysis;
  const sources = registry.filter((r) => r.scenario === "baseline").length;
  return (
    <div className="tiles">
      <div className="tile">
        <div className="tile-top">
          <span className="label">Peak by 2030</span>
          <span className="mini-icon">
            <Icon name="overview" size={16} />
          </span>
        </div>
        <div className="value">
          {(consensus.pBy2030 * 100).toFixed(0)}
          <span>%</span>
        </div>
        <div className="delta">Experimental prototype probability</div>
        <div className="probability-track">
          <span style={{ width: `${consensus.pBy2030 * 100}%` }} />
        </div>
      </div>
      <button className="tile tile-action" onClick={onSources}>
        <div className="tile-top">
          <span className="label">Outlook sources</span>
          <span className="mini-icon">
            <Icon name="sources" size={16} />
          </span>
        </div>
        <div className="value">
          {sources}
        </div>
        <div className="delta">Baseline positions in the blend <Icon name="arrow" size={14} /></div>
      </button>
      <button className="tile tile-action" onClick={() => onNews(false)}>
        <div className="tile-top">
          <span className="label">Screened articles</span>
          <span className="mini-icon">
            <Icon name="news" size={16} />
          </span>
        </div>
        <div className="value">
          {articles.length.toLocaleString()}
        </div>
        <div className="delta">Explore the selected evidence <Icon name="arrow" size={14} /></div>
      </button>
      <button className="tile tile-action" onClick={() => onNews(true)}>
        <div className="tile-top">
          <span className="label">Peak signals</span>
          <span className="mini-icon amber">
            <Icon name="signal" size={16} />
          </span>
        </div>
        <div className="value">
          {claimIds.size}
        </div>
        <div className="delta">Prototype peak-claim detection <Icon name="arrow" size={14} /></div>
      </button>
    </div>
  );
}
