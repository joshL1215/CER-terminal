import type { Article, Feed } from "../data/types";
import { OTHER } from "../model/analysis";
import { categoryColor } from "./VolumeChart";

interface Props {
  articles: Article[];
  feedsById: Map<string, Feed>;
  claimIds: Map<number, number>;
  limit?: number;
}

function formatDate(iso: string | null): string {
  if (!iso) return "undated";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function ArticleFeed({ articles, feedsById, claimIds, limit = 60 }: Props) {
  if (!articles.length) return <div className="empty">No kept articles match these filters.</div>;
  return (
    <div className="feed">
      {articles.slice(0, limit).map((a) => {
        const cat = a.category ?? OTHER;
        const claim = claimIds.get(a.id);
        return (
          <article className="article" key={a.id}>
            <h3>
              <a href={a.url} target="_blank" rel="noopener noreferrer">
                {a.title}
              </a>
            </h3>
            <div className="meta">
              <span>{feedsById.get(a.feed_id)?.name ?? a.feed_id}</span>
              <span>·</span>
              <span>{formatDate(a.published_at)}</span>
              <span className="chip">
                <span className="swatch" style={{ background: categoryColor(cat) }} />
                {cat}
              </span>
              {claim !== undefined && (
                <span className="chip signal" title="This article makes a directional claim about the fossil peak and feeds the media nowcast">
                  ▲ peak signal → {claim}
                </span>
              )}
            </div>
            {a.description && <p>{a.description}</p>}
          </article>
        );
      })}
      {articles.length > limit && <div className="note">Showing the newest {limit} of {articles.length}.</div>}
    </div>
  );
}
